from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def inicio():
    return render_template("index.html")

@app.route('/planta/<nombre>')
def planta(nombre):
    mensaje = f"🌱 Planta: {nombre.capitalize()} registrada en EcoGrow"
    return render_template("planta.html", mensaje=mensaje)

if __name__ == '__main__':
    app.run(debug=True)
