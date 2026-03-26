from flask import Blueprint, flash, redirect, render_template, request, url_for

try:
    from form import ProductoFormData
except ModuleNotFoundError:
    from ..form import ProductoFormData

from .shared import inventario, login_required

inventario_bp = Blueprint("inventario", __name__)


@inventario_bp.route("/inventario")
@inventario_bp.route("/productos")
@login_required
def mostrar_inventario():
    productos = inventario.all()
    return render_template("productos.html", productos=productos)


@inventario_bp.route("/inventario/crear", methods=("GET", "POST"))
@login_required
def crear_producto():
    form_data = ProductoFormData()
    if request.method == "POST":
        form_data = ProductoFormData.from_request(request.form)
        if form_data.is_valid() and form_data.cantidad is not None and form_data.precio is not None:
            try:
                inventario.add(
                    nombre=form_data.nombre,
                    cantidad=form_data.cantidad,
                    precio=form_data.precio,
                    descripcion=form_data.descripcion,
                )
                flash("Producto guardado en SQLite, TXT, JSON y CSV.", "success")
                return redirect(url_for("inventario.mostrar_inventario"))
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


@inventario_bp.route("/inventario/editar/<int:pid>", methods=("GET", "POST"))
@login_required
def editar_producto(pid):
    producto = inventario.get(pid)
    if not producto:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("inventario.mostrar_inventario"))

    if request.method == "POST":
        form_data = ProductoFormData.from_request(request.form)
        if form_data.is_valid() and form_data.cantidad is not None and form_data.precio is not None:
            try:
                inventario.update(
                    pid,
                    nombre=form_data.nombre,
                    cantidad=form_data.cantidad,
                    precio=form_data.precio,
                    descripcion=form_data.descripcion,
                )
                flash("Producto actualizado y archivos sincronizados.", "success")
                return redirect(url_for("inventario.mostrar_inventario"))
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


@inventario_bp.route("/inventario/borrar/<int:pid>", methods=("POST",))
@login_required
def borrar(pid):
    inventario.delete(pid)
    flash("Producto eliminado de SQLite y archivos sincronizados.", "success")
    return redirect(url_for("inventario.mostrar_inventario"))


@inventario_bp.route("/datos")
@login_required
def ver_datos():
    return render_template(
        "datos.html",
        datos_txt=inventario.read_txt(),
        datos_json=inventario.read_json(),
        datos_csv=inventario.read_csv(),
        productos_db=inventario.all(),
    )
