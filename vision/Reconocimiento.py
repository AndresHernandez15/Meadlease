import cv2
import os
import numpy as np
import time


class SistemaReconocimientoMarcoFijo:
    def __init__(self):
        # Cargar detector
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Cargar modelo entrenado
        self.reconocedor = cv2.face.LBPHFaceRecognizer_create()
        self.nombres = {}
        self.cargar_modelo()

        # Configuración del marco
        self.marco_size = 400
        self.umbral_confianza = 70

        # Variables de estado
        self.ultimo_resultado = None
        self.tiempo_ultimo_cambio = time.time()
        self.duracion_mensaje = 2

    # 🔧 FUNCIÓN ARREGLADA (NO SE CAE)
    def cargar_modelo(self):
        modelo_path = "modelo/reconocedor.xml"
        nombres_path = "modelo/nombres.txt"

        if not os.path.exists(modelo_path):
            print(" No se encontró el modelo entrenado")
            return False

        if not os.path.exists(nombres_path):
            print(" No se encontró nombres.txt")
            return False

        self.reconocedor.read(modelo_path)
        self.nombres = {}

        with open(nombres_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()

                if not linea:
                    continue

                if "," not in linea:
                    print("⚠ Línea inválida ignorada:", linea)
                    continue

                try:
                    idx, nombre = linea.split(",", 1)
                    self.nombres[int(idx)] = nombre
                except ValueError:
                    print(" Error procesando línea:", linea)

        print(f" Modelo cargado: {list(self.nombres.values())}")
        return True

    def dibujar_marco_fijo(self, frame, estado="esperando", nombre=None, confianza=None):
        h, w = frame.shape[:2]
        marco_x = (w - self.marco_size) // 2
        marco_y = (h - self.marco_size) // 2

        if estado == "reconocido":
            color_marco = (0, 255, 0)
            grosor = 4
        elif estado == "denegado":
            color_marco = (0, 0, 255)
            grosor = 4
        else:
            color_marco = (255, 255, 255)
            grosor = 3

        cv2.rectangle(frame, (marco_x, marco_y),
                      (marco_x + self.marco_size, marco_y + self.marco_size),
                      color_marco, grosor)

        longitud = 40
        grosor_e = 6

        cv2.line(frame, (marco_x, marco_y),
                 (marco_x + longitud, marco_y), color_marco, grosor_e)
        cv2.line(frame, (marco_x, marco_y),
                 (marco_x, marco_y + longitud), color_marco, grosor_e)

        cv2.line(frame, (marco_x + self.marco_size, marco_y),
                 (marco_x + self.marco_size - longitud, marco_y), color_marco, grosor_e)
        cv2.line(frame, (marco_x + self.marco_size, marco_y),
                 (marco_x + self.marco_size, marco_y + longitud), color_marco, grosor_e)

        cv2.line(frame, (marco_x, marco_y + self.marco_size),
                 (marco_x + longitud, marco_y + self.marco_size), color_marco, grosor_e)
        cv2.line(frame, (marco_x, marco_y + self.marco_size),
                 (marco_x, marco_y + self.marco_size - longitud), color_marco, grosor_e)

        cv2.line(frame, (marco_x + self.marco_size, marco_y + self.marco_size),
                 (marco_x + self.marco_size - longitud, marco_y + self.marco_size),
                 color_marco, grosor_e)
        cv2.line(frame, (marco_x + self.marco_size, marco_y + self.marco_size),
                 (marco_x + self.marco_size, marco_y + self.marco_size - longitud),
                 color_marco, grosor_e)

        if estado == "esperando":
            texto = "Coloca tu rostro en el marco"
            color_texto = (255, 255, 255)
        elif estado == "reconocido":
            texto = "ACCESO PERMITIDO"
            color_texto = (0, 255, 0)
        elif estado == "denegado":
            texto = "ACCESO DENEGADO"
            color_texto = (0, 0, 255)
        else:
            texto = ""

        if texto:
            cv2.rectangle(frame, (marco_x, marco_y - 60),
                          (marco_x + self.marco_size, marco_y - 5),
                          (0, 0, 0), -1)
            cv2.putText(frame, texto,
                        (marco_x + 20, marco_y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, color_texto, 2)

        if nombre and confianza is not None:
            cv2.rectangle(frame,
                          (marco_x, marco_y + self.marco_size + 5),
                          (marco_x + self.marco_size, marco_y + self.marco_size + 80),
                          (0, 0, 0), -1)

            cv2.putText(frame, f"Persona: {nombre}",
                        (marco_x + 10, marco_y + self.marco_size + 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.putText(frame, f"Confianza: {100 - confianza:.1f}%",
                        (marco_x + 10, marco_y + self.marco_size + 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return marco_x, marco_y

    def verificar_rostro_en_marco(self, x, y, w, h, mx, my):
        cx = x + w // 2
        cy = y + h // 2
        return (mx - 50 < cx < mx + self.marco_size + 50 and
                my - 50 < cy < my + self.marco_size + 50)

    def reconocer(self, gray):
        rostros = self.detector.detectMultiScale(gray, 1.3, 5)
        if len(rostros) == 0:
            return None, None, None

        x, y, w, h = max(rostros, key=lambda r: r[2] * r[3])
        rostro = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
        etiqueta, confianza = self.reconocedor.predict(rostro)

        if confianza < self.umbral_confianza:
            return self.nombres.get(etiqueta, "Desconocido"), confianza, (x, y, w, h)
        else:
            return "Desconocido", confianza, (x, y, w, h)

    def iniciar(self):
        cam = cv2.VideoCapture(0)
        estado = "esperando"
        ultimo_nombre = None
        ultima_confianza = None

        while True:
            ret, frame = cam.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            nombre, confianza, coords = self.reconocer(gray)
            mx, my = self.dibujar_marco_fijo(frame, estado, ultimo_nombre, ultima_confianza)

            if coords:
                x, y, w, h = coords
                if self.verificar_rostro_en_marco(x, y, w, h, mx, my):
                    if nombre != "Desconocido":
                        estado = "reconocido"
                        ultimo_nombre = nombre
                        ultima_confianza = confianza
                    else:
                        estado = "denegado"
                        ultimo_nombre = "No autorizado"
                        ultima_confianza = confianza
                    self.tiempo_ultimo_cambio = time.time()
                else:
                    estado = "esperando"
            else:
                if time.time() - self.tiempo_ultimo_cambio > self.duracion_mensaje:
                    estado = "esperando"
                    ultimo_nombre = None
                    ultima_confianza = None

            cv2.imshow("Sistema de Reconocimiento", frame)
            if cv2.waitKey(1) == 27:
                break

        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    SistemaReconocimientoMarcoFijo().iniciar()
