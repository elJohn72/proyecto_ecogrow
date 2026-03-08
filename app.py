from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from form import ProductoFormData
from inventario import Inventario, db, init_app as init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "ecogrow-dev"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{Path(app.root_path) / 'inventario.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

init_db(app)
inventario = Inventario()
with app.app_context():
    inventario.sync_files()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contactos")
def contactos():
    return render_template("contactos.html")


@app.route("/cultivos")
def cultivos():
    return render_template("cultivos.html")


@app.route("/sensores")
def sensores():
    return render_template("sensores.html")


@app.route("/planta/<nombre>")
def planta(nombre):
    mensaje = f"Planta: {nombre.capitalize()} registrada en EcoGrow"
    return render_template("planta.html", mensaje=mensaje)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/irrigation")
def irrigation():
    return render_template("irrigation.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/demo")
def demo():
    return render_template("demo.html")


@app.route("/sustainability")
def sustainability():
    return render_template("sustainability.html")


@app.route("/inventario")
@app.route("/productos")
def mostrar_inventario():
    productos = inventario.all()
    return render_template("productos.html", productos=productos)


@app.route("/inventario/crear", methods=("GET", "POST"))
def crear_producto():
    form_data = ProductoFormData()
    if request.method == "POST":
        form_data = ProductoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                inventario.add(
                    nombre=form_data.nombre,
                    cantidad=form_data.cantidad,
                    precio=form_data.precio,
                    descripcion=form_data.descripcion,
                )
                flash("Producto guardado en SQLite, TXT, JSON y CSV.", "success")
                return redirect(url_for("mostrar_inventario"))
            except ValueError as exc:
                flash(str(exc), "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "producto_form.html",
        titulo="Crear producto",
        accion="Guardar",
        producto=form_data,
        errores=form_data.errors,
    )


@app.route("/inventario/editar/<int:pid>", methods=("GET", "POST"))
def editar_producto(pid):
    producto = inventario.get(pid)
    if not producto:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("mostrar_inventario"))

    if request.method == "POST":
        form_data = ProductoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                inventario.update(
                    pid,
                    nombre=form_data.nombre,
                    cantidad=form_data.cantidad,
                    precio=form_data.precio,
                    descripcion=form_data.descripcion,
                )
                flash("Producto actualizado y archivos sincronizados.", "success")
                return redirect(url_for("mostrar_inventario"))
            except ValueError as exc:
                flash(str(exc), "error")
        else:
            flash("Corrige los errores del formulario.", "error")
    else:
        form_data = ProductoFormData.from_producto(producto)

    return render_template(
        "producto_form.html",
        titulo="Editar producto",
        accion="Actualizar",
        producto=form_data,
        errores=form_data.errors,
    )


@app.route("/inventario/borrar/<int:pid>")
def borrar(pid):
    inventario.delete(pid)
    flash("Producto eliminado de SQLite y archivos sincronizados.", "success")
    return redirect(url_for("mostrar_inventario"))


@app.route("/datos")
def ver_datos():
    return render_template(
        "datos.html",
        datos_txt=inventario.read_txt(),
        datos_json=inventario.read_json(),
        datos_csv=inventario.read_csv(),
        productos_db=inventario.all(),
    )


@app.cli.command("sincronizar-datos")
def sincronizar_datos():
    inventario.sync_files()
    print("Archivos TXT, JSON y CSV sincronizados desde SQLite.")


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
