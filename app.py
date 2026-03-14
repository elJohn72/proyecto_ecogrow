from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from mysql.connector import Error

from Conexión import (
    MYSQL_CONFIG,
    create_mysql_tables,
    delete_mysql_producto,
    delete_mysql_usuario,
    fetch_mysql_producto,
    fetch_mysql_productos,
    fetch_mysql_usuario,
    fetch_mysql_usuarios,
    get_mysql_config_help,
    get_mysql_status,
    insert_mysql_producto,
    insert_mysql_usuario,
    update_mysql_producto,
    update_mysql_usuario,
)
from form import ProductoFormData, UsuarioFormData
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


@app.route("/mysql")
def mysql_dashboard():
    status = get_mysql_status()
    usuarios = []
    productos_mysql = []
    if status["available"]:
        usuarios = fetch_mysql_usuarios()
        productos_mysql = fetch_mysql_productos()

    return render_template(
        "mysql_dashboard.html",
        mysql_status=status,
        mysql_help=get_mysql_config_help(),
        usuarios=usuarios,
        productos_mysql=productos_mysql,
    )


@app.route("/mysql/inicializar")
def inicializar_mysql():
    try:
        create_mysql_tables()
        flash("Base de datos MySQL y tablas verificadas correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo inicializar MySQL: {exc}", "error")
    return redirect(url_for("mysql_dashboard"))


@app.route("/mysql/usuarios")
def listar_usuarios_mysql():
    try:
        usuarios = fetch_mysql_usuarios()
        status = get_mysql_status()
    except Error as exc:
        flash(f"No se pudo consultar usuarios en MySQL: {exc}", "error")
        return redirect(url_for("mysql_dashboard"))

    return render_template(
        "mysql_usuarios.html",
        usuarios=usuarios,
        mysql_status=status,
    )


@app.route("/mysql/usuarios/crear", methods=("GET", "POST"))
def crear_usuario_mysql():
    form_data = UsuarioFormData()
    if request.method == "POST":
        form_data = UsuarioFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                insert_mysql_usuario(
                    nombre=form_data.nombre,
                    mail=form_data.mail,
                    password=form_data.password,
                )
                flash("Usuario guardado en MySQL.", "success")
                return redirect(url_for("listar_usuarios_mysql"))
            except Error as exc:
                flash(f"No se pudo guardar el usuario en MySQL: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "mysql_usuario_form.html",
        titulo="Crear usuario MySQL",
        accion="Guardar",
        usuario=form_data,
        errores=form_data.errors,
    )


@app.route("/mysql/usuarios/editar/<int:uid>", methods=("GET", "POST"))
def editar_usuario_mysql(uid):
    try:
        usuario_mysql = fetch_mysql_usuario(uid)
    except Error as exc:
        flash(f"No se pudo consultar el usuario: {exc}", "error")
        return redirect(url_for("listar_usuarios_mysql"))

    if not usuario_mysql:
        flash("Usuario no encontrado en MySQL.", "error")
        return redirect(url_for("listar_usuarios_mysql"))

    if request.method == "POST":
        form_data = UsuarioFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                update_mysql_usuario(
                    uid,
                    nombre=form_data.nombre,
                    mail=form_data.mail,
                    password=form_data.password,
                )
                flash("Usuario actualizado en MySQL.", "success")
                return redirect(url_for("listar_usuarios_mysql"))
            except Error as exc:
                flash(f"No se pudo actualizar el usuario: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")
    else:
        form_data = UsuarioFormData.from_mysql_usuario(usuario_mysql)

    return render_template(
        "mysql_usuario_form.html",
        titulo="Editar usuario MySQL",
        accion="Actualizar",
        usuario=form_data,
        errores=form_data.errors,
    )


@app.route("/mysql/usuarios/borrar/<int:uid>")
def borrar_usuario_mysql(uid):
    try:
        delete_mysql_usuario(uid)
        flash("Usuario eliminado de MySQL.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el usuario: {exc}", "error")
    return redirect(url_for("listar_usuarios_mysql"))


@app.route("/mysql/productos")
def listar_productos_mysql():
    try:
        productos_mysql = fetch_mysql_productos()
        status = get_mysql_status()
    except Error as exc:
        flash(f"No se pudo consultar productos en MySQL: {exc}", "error")
        return redirect(url_for("mysql_dashboard"))

    return render_template(
        "mysql_productos.html",
        productos_mysql=productos_mysql,
        mysql_status=status,
    )


@app.route("/mysql/productos/crear", methods=("GET", "POST"))
def crear_producto_mysql():
    form_data = ProductoFormData()
    if request.method == "POST":
        form_data = ProductoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                insert_mysql_producto(
                    nombre=form_data.nombre,
                    cantidad=form_data.cantidad,
                    precio=form_data.precio,
                    descripcion=form_data.descripcion,
                )
                flash("Producto guardado en MySQL.", "success")
                return redirect(url_for("listar_productos_mysql"))
            except Error as exc:
                flash(f"No se pudo guardar el producto en MySQL: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "mysql_producto_form.html",
        titulo="Crear producto MySQL",
        accion="Guardar",
        producto=form_data,
        errores=form_data.errors,
    )


@app.route("/mysql/productos/editar/<int:pid>", methods=("GET", "POST"))
def editar_producto_mysql(pid):
    try:
        producto_mysql = fetch_mysql_producto(pid)
    except Error as exc:
        flash(f"No se pudo consultar el producto: {exc}", "error")
        return redirect(url_for("listar_productos_mysql"))

    if not producto_mysql:
        flash("Producto no encontrado en MySQL.", "error")
        return redirect(url_for("listar_productos_mysql"))

    if request.method == "POST":
        form_data = ProductoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                update_mysql_producto(
                    pid,
                    nombre=form_data.nombre,
                    cantidad=form_data.cantidad,
                    precio=form_data.precio,
                    descripcion=form_data.descripcion,
                )
                flash("Producto actualizado en MySQL.", "success")
                return redirect(url_for("listar_productos_mysql"))
            except Error as exc:
                flash(f"No se pudo actualizar el producto: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")
    else:
        form_data = ProductoFormData(
            nombre=producto_mysql["nombre"],
            cantidad=producto_mysql["cantidad"],
            precio=float(producto_mysql["precio"]),
            descripcion=producto_mysql["descripcion"],
        )

    return render_template(
        "mysql_producto_form.html",
        titulo="Editar producto MySQL",
        accion="Actualizar",
        producto=form_data,
        errores=form_data.errors,
    )


@app.route("/mysql/productos/borrar/<int:pid>")
def borrar_producto_mysql(pid):
    try:
        delete_mysql_producto(pid)
        flash("Producto eliminado de MySQL.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el producto: {exc}", "error")
    return redirect(url_for("listar_productos_mysql"))


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


@app.cli.command("mysql-init")
def mysql_init():
    try:
        create_mysql_tables()
        print("MySQL inicializado correctamente.")
        print(
            f"Host: {MYSQL_CONFIG['host']} | "
            f"Usuario: {MYSQL_CONFIG['user']} | "
            f"Base de datos: {MYSQL_CONFIG['database']}"
        )
        print(f"Puerto: {MYSQL_CONFIG['port']} | Socket: {MYSQL_CONFIG['unix_socket']}")
    except Error as exc:
        print(f"No se pudo inicializar MySQL: {exc}")


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
