# Proyecto-Interfaz-gr-fica-para-funciones

Graficador de funciones matemáticas de escritorio con Tkinter, Matplotlib y NumPy.

## Ejecutar

```powershell
python -m pip install -r requirements.txt
python app.py
```

La ventana comienza en 1600 × 900 y se puede redimensionar. La gráfica ocupa el 70 % del ancho y el panel de gestión el 30 %. El botón circular de la esquina inferior derecha del panel lo oculta o vuelve a mostrarlo; cuando está oculto, el botón queda en la esquina inferior derecha de la ventana. El botón de menú de la esquina superior izquierda despliega, por encima de la gráfica, un selector que ocupa el 25 % de la ventana y permite cambiar entre **Funciones**, **Geometría 2D** y **Geometría 3D** sin redimensionar el gráfico. La opción activa permanece marcada. El botón de engranaje abre la configuración, donde se puede activar el modo oscuro, mostrar intersecciones y ajustar los intervalos de X e Y (en Geometría 3D, el intervalo de Y se usa para Z). En **Funciones**, dejar vacíos ambos límites de Y ajusta automáticamente ese intervalo.

La interfaz utiliza una paleta azul celeste inspirada en el logotipo del programa. El logotipo principal se usa como icono de la aplicación y la versión horizontal se muestra junto al encabezado.

En **Funciones**, introduce una expresión en el panel derecho para añadirla a la lista; marca o desmarca cada función para mostrarla u ocultarla. Al añadir la primera función, la gráfica se encuadra automáticamente; usa el botón de inicio de la barra de Matplotlib para volver a encuadrar las funciones visibles. En **Geometría 2D** puedes insertar puntos, círculos (centro y radio) y rectángulos (origen, ancho y alto). En **Geometría 3D** puedes insertar esferas (centro y radio) y planos de la forma `z = ax + by + c`. Los parámetros se pueden editar antes de insertar cada figura y las figuras se pueden ocultar o quitar desde su lista.

Activa **Mostrar intersecciones** para listar y marcar los cruces de las funciones visibles dentro del intervalo actual. Cada punto tiene una etiqueta automática (`A`, `B`, `C`, etc.) y la tabla muestra sus coordenadas y las funciones que se cruzan. Mueve el cursor sobre la gráfica para consultar las coordenadas; la barra de Matplotlib permite acercar, desplazar y restablecer la vista.

Cada función recibe un identificador único (`f(x)`, `g(x)`, `h(x)`, etc.). Pulsa el botón **ⓘ** junto a una función para ver sus características: pendiente e intersecciones para polinomios de grado 1; concavidad, vértice, intersecciones y eje de simetría para grado 2; e intersecciones y punto de inflexión para grado 3. Para funciones no polinómicas, las intersecciones con X se aproximan dentro del intervalo visible. La ventana de información se abre centrada sobre la aplicación.

Se admiten polinomios de cualquier grado, potencias y exponenciales, logaritmos, funciones trigonométricas y operaciones aritméticas. Ejemplos: `x^3 - 2x + 1`, `2^x`, `e^x`, `ln(x)`, `log(x)`, `log(x, 2)`, `sin(x)` y `sqrt(abs(x))`. `log(x)` es base 10; `ln(x)` es el logaritmo natural. La multiplicación explícita y la forma implícita (`2x`) son válidas.

Las expresiones se validan con una gramática restringida y no se ejecutan como código Python.

## Pruebas

```powershell
python -m unittest discover -v
```