from flask import Flask, render_template

app = Flask(__name__)


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


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
