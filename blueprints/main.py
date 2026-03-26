from flask import Blueprint, redirect, render_template, request, session, url_for

from .shared import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def inicio():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/contactos")
def contactos():
    return render_template("contactos.html")


@main_bp.route("/planta/<nombre>")
def planta(nombre):
    mensaje = f"Planta: {nombre.capitalize()} registrada en EcoGrow"
    return render_template("planta.html", mensaje=mensaje)


@main_bp.route("/demo")
def demo():
    return render_template("demo.html")


@main_bp.route("/modo/<mode>")
@login_required
def set_mode(mode):
    session["ui_mode"] = "admin" if mode == "admin" else "user"
    return redirect(request.referrer or url_for("torres.dashboard"))
