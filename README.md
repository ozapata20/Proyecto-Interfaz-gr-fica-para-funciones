# Proyecto-Interfaz-gr-fica-para-funciones

Graficador de funciones matemáticas de escritorio con Tkinter, Matplotlib y NumPy.

## Ejecutar

```powershell
python -m pip install -r requirements.txt
python app.py
```

La ventana comienza en 1600 × 900 y se puede redimensionar. La gráfica ocupa el 70 % del ancho y el panel de funciones el 30 %. El botón circular de la esquina inferior derecha del panel de funciones lo oculta o vuelve a mostrarlo; cuando está oculto, el botón queda en la esquina inferior derecha de la ventana. El botón de engranaje abre la configuración, donde se puede activar el modo oscuro, mostrar intersecciones y ajustar los intervalos de X e Y. Si se dejan vacíos ambos límites de Y, la gráfica ajusta ese intervalo automáticamente. Al añadir la primera función, la gráfica se encuadra automáticamente; usa el botón de inicio de la barra de Matplotlib para volver a encuadrar las funciones visibles. Introduce una expresión en el panel derecho para añadirla a la lista; marca o desmarca cada función para mostrarla u ocultarla.

Activa **Mostrar intersecciones** para listar y marcar los cruces de las funciones visibles dentro del intervalo actual. Cada punto tiene una etiqueta automática (`A`, `B`, `C`, etc.) y la tabla muestra sus coordenadas y las funciones que se cruzan. Mueve el cursor sobre la gráfica para consultar las coordenadas; la barra de Matplotlib permite acercar, desplazar y restablecer la vista.

Cada función recibe un identificador único (`f(x)`, `g(x)`, `h(x)`, etc.). Pulsa el botón **ⓘ** junto a una función para ver sus características: pendiente e intersecciones para polinomios de grado 1; concavidad, vértice, intersecciones y eje de simetría para grado 2; e intersecciones y punto de inflexión para grado 3. Para funciones no polinómicas, las intersecciones con X se aproximan dentro del intervalo visible. La ventana de información se abre centrada sobre la aplicación.

Se admiten polinomios de cualquier grado, potencias y exponenciales, logaritmos, funciones trigonométricas y operaciones aritméticas. Ejemplos: `x^3 - 2x + 1`, `2^x`, `e^x`, `ln(x)`, `log(x)`, `log(x, 2)`, `sin(x)` y `sqrt(abs(x))`. `log(x)` es base 10; `ln(x)` es el logaritmo natural. La multiplicación explícita y la forma implícita (`2x`) son válidas.

Las expresiones se validan con una gramática restringida y no se ejecutan como código Python.

## Pruebas

```powershell
python -m unittest discover -v
```