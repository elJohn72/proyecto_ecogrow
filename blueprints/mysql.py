from flask import Blueprint, flash, redirect, render_template, request, url_for
from mysql.connector import Error

try:
    from Conexión import (
        create_mysql_tables,
        delete_mysql_usuario,
        fetch_mysql_usuario,
        fetch_mysql_usuarios,
        get_mysql_config_help,
        get_mysql_status,
        insert_mysql_usuario,
        update_mysql_usuario,
    )
    from forms import UsuarioFormData
except ModuleNotFoundError:
    from ..Conexión import (
        create_mysql_tables,
        delete_mysql_usuario,
        fetch_mysql_usuario,
        fetch_mysql_usuarios,
        get_mysql_config_help,
        get_mysql_status,
        insert_mysql_usuario,
        update_mysql_usuario,
    )
    from ..forms import UsuarioFormData

from .shared import admin_required, login_required

mysql_bp = Blueprint("mysql", __name__)


@mysql_bp.route("/mysql")
@login_required
@admin_required
def mysql_dashboard():
    status = get_mysql_status()
    usuarios = []
    if status["available"]:
        usuarios = fetch_mysql_usuarios()

    return render_template(
        "mysql_dashboard.html",
        mysql_status=status,
        mysql_help=get_mysql_config_help(),
        usuarios=usuarios,
    )


@mysql_bp.route("/mysql/inicializar")
@login_required
@admin_required
def inicializar_mysql():
    try:
        create_mysql_tables()
        flash("Base de datos MySQL y tablas verificadas correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo inicializar MySQL: {exc}", "error")
    return redirect(url_for("mysql.mysql_dashboard"))


@mysql_bp.route("/mysql/usuarios")
@login_required
@admin_required
def listar_usuarios_mysql():
    try:
        usuarios = fetch_mysql_usuarios()
        status = get_mysql_status()
    except Error as exc:
        flash(f"No se pudo consultar usuarios en MySQL: {exc}", "error")
        return redirect(url_for("mysql.mysql_dashboard"))

    return render_template("mysql_usuarios.html", usuarios=usuarios, mysql_status=status)


@mysql_bp.route("/mysql/usuarios/crear", methods=("GET", "POST"))
@login_required
@admin_required
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
                return redirect(url_for("mysql.listar_usuarios_mysql"))
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


@mysql_bp.route("/mysql/usuarios/editar/<int:uid>", methods=("GET", "POST"))
@login_required
@admin_required
def editar_usuario_mysql(uid):
    try:
        usuario_mysql = fetch_mysql_usuario(uid)
    except Error as exc:
        flash(f"No se pudo consultar el usuario: {exc}", "error")
        return redirect(url_for("mysql.listar_usuarios_mysql"))

    if not usuario_mysql:
        flash("Usuario no encontrado en MySQL.", "error")
        return redirect(url_for("mysql.listar_usuarios_mysql"))

    if request.method == "POST":
        form_data = UsuarioFormData.from_request(request.form, password_required=False)
        if form_data.is_valid():
            try:
                update_mysql_usuario(
                    uid,
                    nombre=form_data.nombre,
                    mail=form_data.mail,
                    password=form_data.password or None,
                )
                flash("Usuario actualizado en MySQL.", "success")
                return redirect(url_for("mysql.listar_usuarios_mysql"))
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


@mysql_bp.route("/mysql/usuarios/borrar/<int:uid>", methods=("POST",))
@login_required
@admin_required
def borrar_usuario_mysql(uid):
    try:
        delete_mysql_usuario(uid)
        flash("Usuario eliminado de MySQL.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el usuario: {exc}", "error")
    return redirect(url_for("mysql.listar_usuarios_mysql"))
