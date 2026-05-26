from flask import Blueprint, Response, redirect, render_template, request, session, url_for

from .shared import is_admin_user, login_required

main_bp = Blueprint("main", __name__)

PUBLIC_SITEMAP_ENDPOINTS = (
    "main.inicio",
    "main.about",
    "main.contactos",
    "main.demo",
    "main.privacidad",
    "auth.login",
    "auth.registro",
)


@main_bp.route("/")
def inicio():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/contactos")
def contactos():
    return render_template("contactos.html")


@main_bp.route("/privacidad")
def privacidad():
    return render_template("privacidad.html")


@main_bp.route("/planta/<nombre>")
def planta(nombre):
    mensaje = f"Planta: {nombre.capitalize()} registrada en EcoGrow"
    return render_template("planta.html", mensaje=mensaje)


@main_bp.route("/demo")
def demo():
    return render_template("demo.html")


@main_bp.route("/robots.txt")
def robots_txt():
    sitemap_url = url_for("main.sitemap_xml", _external=True)
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /dashboard\n"
        "Disallow: /torres\n"
        "Disallow: /cultivos\n"
        "Disallow: /sensores\n"
        "Disallow: /mysql\n"
        "Disallow: /api/\n"
        "Disallow: /agricultor-ia\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return Response(body, mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap_xml():
    urls = [url_for(endpoint, _external=True) for endpoint in PUBLIC_SITEMAP_ENDPOINTS]
    entries = "".join(f"  <url><loc>{loc}</loc></url>\n" for loc in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}"
        "</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@main_bp.route("/modo/<mode>")
@login_required
def set_mode(mode):
    if mode == "admin" and is_admin_user():
        session["ui_mode"] = "admin"
    else:
        session["ui_mode"] = "user"
    return redirect(request.referrer or url_for("torres.dashboard"))
