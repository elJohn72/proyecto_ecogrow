from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user
from mysql.connector import Error

try:
    from Conexión import (
        fetch_mysql_user_by_mail,
        fetch_torres_by_user,
        insert_mysql_usuario,
        verify_mysql_user_credentials,
    )
    from forms import LoginFormData, UsuarioFormData
    from models import User
except ModuleNotFoundError:
    from ..Conexión import (
        fetch_mysql_user_by_mail,
        fetch_torres_by_user,
        insert_mysql_usuario,
        verify_mysql_user_credentials,
    )
    from ..forms import LoginFormData, UsuarioFormData
    from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=("GET", "POST"))
def login():
    form_data = LoginFormData()
    if request.method == "POST":
        form_data = LoginFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                usuario = verify_mysql_user_credentials(form_data.mail, form_data.password)
                torres_usuario = fetch_torres_by_user(usuario["id_usuario"]) if usuario else []
            except Error as exc:
                flash(f"No se pudo validar el acceso: {exc}", "error")
                return render_template("login.html", form_data=form_data, errores=form_data.errors)

            if usuario:
                login_user(User.from_mysql_row(usuario))
                if torres_usuario:
                    session["torre_id"] = torres_usuario[0]["id_torre"]
                    flash(f"Bienvenido, {usuario['nombre']}. Torre activa: {torres_usuario[0]['nombre']}.", "success")
                    return redirect(url_for("torres.dashboard"))
                flash(f"Bienvenido, {usuario['nombre']}.", "success")
                return redirect(url_for("torres.torres"))

            flash("Credenciales incorrectas.", "error")
        else:
            flash("Completa correo y contrasena.", "error")

    return render_template("login.html", form_data=form_data, errores=form_data.errors)


@auth_bp.route("/registro", methods=("GET", "POST"))
def registro():
    form_data = UsuarioFormData()
    if request.method == "POST":
        form_data = UsuarioFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                usuario_existente = fetch_mysql_user_by_mail(form_data.mail)
                if usuario_existente:
                    flash("Ya existe una cuenta con ese correo.", "error")
                    return render_template("registro.html", usuario=form_data, errores=form_data.errors)

                usuario_id = insert_mysql_usuario(
                    nombre=form_data.nombre,
                    mail=form_data.mail,
                    password=form_data.password,
                )
                login_user(User(usuario_id, form_data.nombre, form_data.mail))
                flash("Tu cuenta fue creada correctamente. Ahora registra tu torre.", "success")
                return redirect(url_for("torres.registrar_torre"))
            except Error as exc:
                flash(f"No se pudo crear la cuenta: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template("registro.html", usuario=form_data, errores=form_data.errors)


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Sesion cerrada correctamente.", "success")
    return redirect(url_for("main.inicio"))
