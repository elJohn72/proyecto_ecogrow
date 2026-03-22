from flask import Blueprint, render_template

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
