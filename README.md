# Proyecto-Interfaz-gr-fica-para-funciones

Graficador de funciones matemáticas de escritorio con Tkinter, Matplotlib y NumPy.

## Ejecutar

```powershell
python -m pip install -r requirements.txt
python app.py
```

La ventana comienza en 1600 × 900 y se puede redimensionar. Introduce una expresión en el panel derecho para añadirla a la lista; marca o desmarca cada función para mostrarla u ocultarla. El intervalo horizontal también se puede ajustar.

Se admiten polinomios de cualquier grado, potencias y exponenciales, logaritmos, funciones trigonométricas y operaciones aritméticas. Ejemplos: `x^3 - 2x + 1`, `2^x`, `e^x`, `ln(x)`, `log(x)`, `log(x, 2)`, `sin(x)` y `sqrt(abs(x))`. `log(x)` es base 10; `ln(x)` es el logaritmo natural. La multiplicación explícita y la forma implícita (`2x`) son válidas.

Las expresiones se validan con una gramática restringida y no se ejecutan como código Python.

## Pruebas

```powershell
python -m unittest discover -v
```