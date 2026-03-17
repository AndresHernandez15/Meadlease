import cv2
import os
import numpy as np


def registrar_y_entrenar():
    print("\n" + "=" * 70)
    print("REGISTRO Y ENTRENAMIENTO DE USUARIO")
    print("=" * 70)

    nombre = input("\nIngresa el nombre del usuario: ").strip()

    if not nombre:
        print("ERROR: Nombre invalido")
        return

    ruta = f"dataset/{nombre}"

    if os.path.exists(ruta):
        imagenes_existentes = [f for f in os.listdir(ruta) if f.endswith('.jpg')]
        num_existentes = len(imagenes_existentes)

        print(f"\nUsuario '{nombre}' ya existe con {num_existentes} fotos")
        print("1. Agregar mas fotos (reentrenamiento)")
        print("2. Borrar y empezar de cero")
        print("3. Cancelar")

        opcion = input("\nSelecciona opcion: ").strip()

        if opcion == "1":
            print(f"\nAGREGANDO MAS FOTOS A {nombre}")
            contador_inicial = num_existentes
        elif opcion == "2":
            import shutil
            shutil.rmtree(ruta)
            os.makedirs(ruta, exist_ok=True)
            contador_inicial = 0
            print(f"\nREGISTRANDO {nombre} DESDE CERO")
        else:
            print("Cancelado")
            return
    else:
        os.makedirs(ruta, exist_ok=True)
        contador_inicial = 0
        print(f"\nNUEVO REGISTRO: {nombre}")

    print("\n" + "=" * 70)
    print(f"CAPTURANDO FOTOS DE {nombre}")
    print("=" * 70)
    print("Preparando camara...")

    cam = cv2.VideoCapture(0)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    max_fotos = 200
    contador = contador_inicial
    frame_counter = 0
    capturar_cada = 3

    input("\nPresiona ENTER cuando estes listo...")

    print("\nCapturando en 3 segundos...")
    import time
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)

    print("\nCAPTURANDO!\n")

    while contador < (contador_inicial + max_fotos):
        ret, frame = cam.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        rostros = detector.detectMultiScale(gray, 1.3, 5)

        h, w = frame.shape[:2]
        marco_size = 350
        marco_x = (w - marco_size) // 2
        marco_y = (h - marco_size) // 2

        fotos_capturadas = contador - contador_inicial
        progreso = (fotos_capturadas / max_fotos) * 100

        if progreso < 50:
            color_marco = (0, 165, 255)
        else:
            color_marco = (0, 255, 0)

        cv2.rectangle(frame, (marco_x, marco_y),
                      (marco_x + marco_size, marco_y + marco_size),
                      color_marco, 3)

        cv2.putText(frame, f"{fotos_capturadas}/{max_fotos}", (marco_x, marco_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        barra_w = 400
        barra_h = 25
        barra_x = (w - barra_w) // 2
        barra_y = h - 50

        cv2.rectangle(frame, (barra_x, barra_y),
                      (barra_x + barra_w, barra_y + barra_h), (50, 50, 50), -1)

        progreso_w = int((fotos_capturadas / max_fotos) * barra_w)
        cv2.rectangle(frame, (barra_x, barra_y),
                      (barra_x + progreso_w, barra_y + barra_h), color_marco, -1)

        if len(rostros) > 0:
            x, y, w_r, h_r = max(rostros, key=lambda r: r[2] * r[3])

            cv2.rectangle(frame, (x, y), (x + w_r, y + h_r), (0, 255, 0), 2)

            frame_counter += 1
            if frame_counter >= capturar_cada:
                frame_counter = 0

                rostro = gray[y:y + h_r, x:x + w_r]
                rostro = cv2.resize(rostro, (200, 200))

                filename = os.path.join(ruta, f"{contador:04d}.jpg")
                cv2.imwrite(filename, rostro)

                contador += 1
                print(f"{fotos_capturadas}/{max_fotos} ({progreso:.0f}%)", end='\r')

        cv2.imshow('Captura', frame)

        if cv2.waitKey(1) == 27:
            break

    cam.release()
    cv2.destroyAllWindows()

    total_fotos = len([f for f in os.listdir(ruta) if f.endswith('.jpg')])

    print(f"\n\nCaptura completada")
    print(f"Total de fotos: {total_fotos}")

    if total_fotos < 100:
        print("ADVERTENCIA: Pocas fotos capturadas")
        return

    print("\n" + "=" * 70)
    print("ENTRENANDO MODELO")
    print("=" * 70)

    rostros = []

    for img_name in os.listdir(ruta):
        if img_name.endswith('.jpg'):
            img_path = os.path.join(ruta, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if img is not None:
                rostros.append(img)

    print(f"\nEntrenando con {len(rostros)} imagenes...")

    reconocedor = cv2.face.LBPHFaceRecognizer_create()
    etiquetas = np.zeros(len(rostros), dtype=np.int32)
    reconocedor.train(rostros, etiquetas)

    os.makedirs("modelos", exist_ok=True)

    nombre_modelo = f"modelos/modelo_{nombre}.xml"
    reconocedor.write(nombre_modelo)

    archivo_nombre = f"modelos/nombre_{nombre}.txt"
    with open(archivo_nombre, "w") as f:
        f.write(nombre)

    print("\n" + "=" * 70)
    print("PROCESO COMPLETADO")
    print("=" * 70)
    print(f"Usuario: {nombre}")
    print(f"Fotos: {len(rostros)}")
    print(f"Modelo: {nombre_modelo}")
    print("=" * 70)


if __name__ == "__main__":
    registrar_y_entrenar()