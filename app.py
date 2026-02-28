from flask import Flask, render_template, request, redirect, url_for

# dominio de inventario
from models import init_db, Producto, Inventario

app = Flask(__name__)

# inicialización de bases de datos y carga en memoria
init_db()
inv = Inventario()


@app.route('/')
def inicio():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/cultivos')
def cultivos():
    return render_template("cultivos.html")


@app.route('/sensores')
def sensores():
    return render_template("sensores.html")


@app.route('/planta/<nombre>')
def planta(nombre):
    mensaje = f"Planta: {nombre.capitalize()} registrada en EcoGrow"
    return render_template("planta.html", mensaje=mensaje)


@app.route('/login')
def login():
    # la plantilla login.html debe heredar de base.html y ofrecer el formulario de acceso
    return render_template('login.html')


@app.route('/irrigation')
def irrigation():
    # placeholder page based on el diseño de irrigation & automation control
    return render_template('irrigation.html')

@app.route('/dashboard')
def dashboard():
    # another example page (main IoT dashboard)
    return render_template('dashboard.html')

@app.route('/demo')
def demo():
    # simple demo page
    return render_template('demo.html')


# --- inventario crud -----------------------------------------------------
@app.route('/inventario')
def mostrar_inventario():
    productos = inv.all()
    return render_template('inventario.html', productos=productos)

@app.route('/inventario/crear', methods=('GET','POST'))
def crear_producto():
    if request.method == 'POST':
        p = Producto(
            nombre=request.form['nombre'],
            cantidad=int(request.form['cantidad']),
            precio=float(request.form['precio'])
        )
        inv.add(p)
        return redirect(url_for('mostrar_inventario'))
    return render_template('crear_producto.html')

@app.route('/inventario/borrar/<int:pid>')
def borrar(pid):
    inv.delete(pid)
    return redirect(url_for('mostrar_inventario'))

# ruta de edición básica (cantidad y precio)
@app.route('/inventario/editar/<int:pid>', methods=('GET','POST'))
def editar_producto(pid):
    producto = inv.productos.get(pid)
    if not producto:
        return redirect(url_for('mostrar_inventario'))
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.cantidad = int(request.form['cantidad'])
        producto.precio = float(request.form['precio'])
        inv.update(pid, nombre=producto.nombre, cantidad=producto.cantidad, precio=producto.precio)
        return redirect(url_for('mostrar_inventario'))
    return render_template('editar_producto.html', producto=producto)

# ------------------------------------------------------------------------

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
