import cv2
import mediapipe as mp
from datetime import datetime
import time


class DetectorHumanos:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils

        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
            model_complexity=1
        )

        self.frames_sin_deteccion = 0
        self.frames_con_deteccion = 0
        self.umbral_confirmacion = 5

        self.es_humano = False
        self.confianza = 0.0

        self.log_detecciones = []

    def verificar_pose_humana(self, landmarks):
        if not landmarks:
            return False, 0.0

        try:
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
            left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
            right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]

            nariz_arriba = nose.y < ((left_hip.y + right_hip.y) / 2)

            ancho_hombros = abs(left_shoulder.x - right_shoulder.x)
            ancho_caderas = abs(left_hip.x - right_hip.x)
            proporcion_hombros = ancho_hombros / (ancho_caderas + 0.0001)
            hombros_correctos = 0.8 < proporcion_hombros < 2.0

            altura_cuerpo = abs(nose.y - ((left_ankle.y + right_ankle.y) / 2))
            piernas_verticales = altura_cuerpo > 0.3

            visibilidad_minima = 0.5
            puntos_visibles = (
                    nose.visibility > visibilidad_minima and
                    left_shoulder.visibility > visibilidad_minima and
                    right_shoulder.visibility > visibilidad_minima
            )

            checks_pasados = sum([
                nariz_arriba,
                hombros_correctos,
                piernas_verticales,
                puntos_visibles
            ])

            confianza = checks_pasados / 4.0
            es_humano = checks_pasados >= 3

            return es_humano, confianza

        except:
            return False, 0.0

    def procesar_frame(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.pose.process(rgb)

        humano_detectado = False
        confianza_frame = 0.0

        if results.pose_landmarks:
            humano_detectado, confianza_frame = self.verificar_pose_humana(
                results.pose_landmarks.landmark
            )

            if humano_detectado:
                self.frames_con_deteccion += 1
                self.frames_sin_deteccion = 0

                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=3),
                    self.mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=3)
                )
            else:
                self.frames_sin_deteccion += 1
                self.frames_con_deteccion = 0
        else:
            self.frames_sin_deteccion += 1
            self.frames_con_deteccion = 0

        if self.frames_con_deteccion >= self.umbral_confirmacion:
            self.es_humano = True
            self.confianza = confianza_frame
        elif self.frames_sin_deteccion >= self.umbral_confirmacion:
            self.es_humano = False
            self.confianza = 0.0

        return frame

    def dibujar_interfaz(self, frame):
        h, w = frame.shape[:2]

        if self.es_humano:
            color_fondo = (0, 100, 0)
            color_texto = (0, 255, 0)
            estado = "HUMANO DETECTADO"
        else:
            color_fondo = (0, 0, 100)
            color_texto = (0, 0, 255)
            estado = "NO ES HUMANO"

        overlay = frame.copy()
        cv2.rectangle(overlay, (50, 30), (w - 50, 180), color_fondo, -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        cv2.rectangle(frame, (50, 30), (w - 50, 180), color_texto, 5)

        cv2.putText(frame, "DETECTOR DE HUMANOS", (w // 2 - 280, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

        cv2.putText(frame, estado, (w // 2 - 250, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, color_texto, 4)

        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (20, 200), (450, 380), (0, 0, 0), -1)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)

        y = 240
        info = [
            f"Estado: {'HUMANO' if self.es_humano else 'ANIMAL/OBJETO'}",
            f"Confianza: {self.confianza * 100:.1f}%",
            f"Frames confirmados: {self.frames_con_deteccion}",
            f"",
            "Detecta:",
            "  - Humanos (de pie, sentados)",
            "  - Rechaza: Perros, gatos, aves",
            "  - Rechaza: Objetos en movimiento"
        ]

        for texto in info:
            cv2.putText(frame, texto, (30, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y += 30

        cv2.putText(frame, "ESC = Salir", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame

    def registrar_deteccion(self):
        registro = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'es_humano': self.es_humano,
            'confianza': self.confianza
        }
        self.log_detecciones.append(registro)

        if self.es_humano:
            print(f"OK {registro['timestamp']} | HUMANO | Confianza: {self.confianza * 100:.1f}%")
        else:
            print(f"NO {registro['timestamp']} | NO HUMANO")

    def iniciar_camara(self):
        cam = cv2.VideoCapture(0)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print("=" * 70)
        print("DETECTOR DE HUMANOS vs ANIMALES")
        print("=" * 70)
        print("Objetivo: Identificar SOLO humanos")
        print("Rechaza: Perros, gatos, pajaros, objetos")
        print("-" * 70)
        print("ESC = Salir")
        print("=" * 70)

        ultimo_registro = time.time()
        intervalo_registro = 3

        while True:
            ret, frame = cam.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)

            frame = self.procesar_frame(frame)
            frame = self.dibujar_interfaz(frame)

            if time.time() - ultimo_registro > intervalo_registro:
                self.registrar_deteccion()
                ultimo_registro = time.time()

            cv2.imshow('Detector de Humanos - ESC para salir', frame)

            if cv2.waitKey(1) == 27:
                break

        cam.release()
        cv2.destroyAllWindows()
        self.pose.close()

        print("\n" + "=" * 70)
        print("RESUMEN DE SESION")
        print("=" * 70)
        print(f"Total detecciones registradas: {len(self.log_detecciones)}")
        humanos = sum(1 for d in self.log_detecciones if d['es_humano'])
        print(f"Humanos detectados: {humanos}")
        print(f"No humanos: {len(self.log_detecciones) - humanos}")
        print("=" * 70)


if __name__ == "__main__":
    detector = DetectorHumanos()
    detector.iniciar_camara()