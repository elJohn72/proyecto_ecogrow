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
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
