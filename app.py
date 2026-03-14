from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from mysql.connector import Error

from Conexión import (
    MYSQL_CONFIG,
    close_active_cycle,
    create_mysql_tables,
    delete_cultivo,
    delete_mysql_producto,
    delete_mysql_usuario,
    fetch_active_cycle_by_torre,
    fetch_cultivo,
    fetch_cultivos,
    fetch_cycles_by_torre,
    fetch_latest_sensor_reading,
    fetch_latest_sensor_reading_by_torre,
    fetch_mysql_producto,
    fetch_mysql_productos,
    fetch_mysql_user_by_mail,
    fetch_mysql_user_by_credentials,
    fetch_mysql_usuario,
    fetch_mysql_usuarios,
    fetch_sensor_readings,
    fetch_sensor_readings_by_torre,
    fetch_torre,
    fetch_torres_by_user,
    get_mysql_config_help,
    get_mysql_status,
    insert_cultivo,
    insert_sensor_reading,
    insert_mysql_producto,
    insert_mysql_usuario,
    register_torre,
    start_cultivo_cycle,
    update_cultivo,
    update_mysql_producto,
    update_mysql_usuario,
)
from form import (
    CicloCultivoFormData,
    CultivoFormData,
    LoginFormData,
    ProductoFormData,
    TorreFormData,
    UsuarioFormData,
)
from inventario import Inventario, init_app as init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "ecogrow-dev"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{Path(app.root_path) / 'inventario.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

init_db(app)
inventario = Inventario()
with app.app_context():
    inventario.sync_files()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Inicia sesion para acceder al panel de gestion.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def _current_user_id() -> int | None:
    user_id = session.get("user_id")
    return int(user_id) if user_id else None


def _current_torre():
    torre_id = session.get("torre_id")
    if not torre_id:
        return None
    try:
        return fetch_torre(int(torre_id))
    except Error:
        return None


def tower_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Inicia sesion para acceder al panel de gestion.", "error")
            return redirect(url_for("login"))

        torre = _current_torre()
        if not torre:
            flash("Primero registra o selecciona tu torre hidropónica.", "error")
            return redirect(url_for("torres"))

        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_layout_state():
    torre = _current_torre() if session.get("user_id") else None
    return {
        "is_authenticated": bool(session.get("user_id")),
        "current_user_name": session.get("user_name"),
        "current_torre": torre,
    }


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contactos")
def contactos():
    return render_template("contactos.html")


@app.route("/login", methods=("GET", "POST"))
def login():
    form_data = LoginFormData()
    if request.method == "POST":
        form_data = LoginFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                usuario = fetch_mysql_user_by_credentials(form_data.mail, form_data.password)
                torres_usuario = fetch_torres_by_user(usuario["id_usuario"]) if usuario else []
            except Error as exc:
                flash(f"No se pudo validar el acceso: {exc}", "error")
                return render_template("login.html", form_data=form_data, errores=form_data.errors)

            if usuario:
                session["user_id"] = usuario["id_usuario"]
                session["user_name"] = usuario["nombre"]
                session["user_mail"] = usuario["mail"]
                if torres_usuario:
                    session["torre_id"] = torres_usuario[0]["id_torre"]
                    flash(f"Bienvenido, {usuario['nombre']}. Torre activa: {torres_usuario[0]['nombre']}.", "success")
                    return redirect(url_for("dashboard"))
                flash(f"Bienvenido, {usuario['nombre']}.", "success")
                return redirect(url_for("torres"))

            flash("Credenciales incorrectas.", "error")
        else:
            flash("Completa correo y contrasena.", "error")

    return render_template("login.html", form_data=form_data, errores=form_data.errors)


@app.route("/registro", methods=("GET", "POST"))
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
                session["user_id"] = usuario_id
                session["user_name"] = form_data.nombre
                session["user_mail"] = form_data.mail
                flash("Tu cuenta fue creada correctamente. Ahora registra tu torre.", "success")
                return redirect(url_for("registrar_torre"))
            except Error as exc:
                flash(f"No se pudo crear la cuenta: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template("registro.html", usuario=form_data, errores=form_data.errors)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada correctamente.", "success")
    return redirect(url_for("inicio"))


@app.route("/torres")
@login_required
def torres():
    try:
        torres_usuario = fetch_torres_by_user(_current_user_id())
    except Error as exc:
        flash(f"No se pudieron consultar tus torres: {exc}", "error")
        torres_usuario = []

    return render_template("torres.html", torres=torres_usuario)


@app.route("/torres/registrar", methods=("GET", "POST"))
@login_required
def registrar_torre():
    form_data = TorreFormData()
    if request.method == "POST":
        form_data = TorreFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                torre_id = register_torre(
                    codigo_unico=form_data.codigo_unico,
                    nombre=form_data.nombre,
                    ubicacion=form_data.ubicacion,
                    usuario_id=_current_user_id(),
                )
                session["torre_id"] = torre_id
                flash("La torre quedó registrada y seleccionada para tu cuenta.", "success")
                return redirect(url_for("elegir_cultivo_actual"))
            except ValueError as exc:
                flash(str(exc), "error")
            except Error as exc:
                flash(f"No se pudo registrar la torre: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "torre_form.html",
        titulo="Registrar torre hidropónica",
        accion="Guardar torre",
        torre=form_data,
        errores=form_data.errors,
    )


@app.route("/torres/seleccionar/<int:torre_id>")
@login_required
def seleccionar_torre(torre_id):
    try:
        torre = fetch_torre(torre_id)
    except Error as exc:
        flash(f"No se pudo consultar la torre: {exc}", "error")
        return redirect(url_for("torres"))

    if not torre or torre["usuario_id"] != _current_user_id():
        flash("La torre solicitada no pertenece a tu cuenta.", "error")
        return redirect(url_for("torres"))

    session["torre_id"] = torre_id
    flash(f"Torre activa: {torre['nombre']}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/torres/cultivo", methods=("GET", "POST"))
@login_required
@tower_required
def elegir_cultivo_actual():
    torre = _current_torre()
    try:
        catalogo = fetch_cultivos()
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        historial_ciclos = fetch_cycles_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudo cargar la configuración de cultivo: {exc}", "error")
        return redirect(url_for("dashboard"))

    form_data = CicloCultivoFormData.from_mysql_ciclo(ciclo_activo) if ciclo_activo else CicloCultivoFormData()

    if request.method == "POST":
        form_data = CicloCultivoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                start_cultivo_cycle(
                    torre_id=torre["id_torre"],
                    cultivo_id=form_data.cultivo_id,
                    fase=form_data.fase,
                    notas=form_data.notas,
                )
                flash("La fase de cultivo de esta torre fue actualizada.", "success")
                return redirect(url_for("dashboard"))
            except Error as exc:
                flash(f"No se pudo actualizar la fase de cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "ciclo_form.html",
        titulo="Elegir cultivo para hoy",
        accion="Guardar fase",
        ciclo=form_data,
        errores=form_data.errors,
        cultivos=catalogo,
        ciclo_activo=ciclo_activo,
        historial_ciclos=historial_ciclos,
        torre=torre,
    )


@app.route("/torres/cultivo/finalizar")
@login_required
@tower_required
def finalizar_ciclo_torre():
    torre = _current_torre()
    try:
        close_active_cycle(torre["id_torre"])
        flash("La fase activa de la torre fue finalizada.", "success")
    except Error as exc:
        flash(f"No se pudo finalizar la fase activa: {exc}", "error")
    return redirect(url_for("elegir_cultivo_actual"))


@app.route("/dashboard")
@login_required
@tower_required
def dashboard():
    torre = _current_torre()
    try:
        cultivos = fetch_cultivos()
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudo cargar el dashboard: {exc}", "error")
        cultivos = []
        ciclo_activo = None
        ultima_lectura = None

    return render_template(
        "dashboard.html",
        cultivos=cultivos,
        ciclo_activo=ciclo_activo,
        torre=torre,
        ultima_lectura=ultima_lectura,
    )


@app.route("/cultivos")
@login_required
@tower_required
def cultivos():
    torre = _current_torre()
    try:
        cultivos_registrados = fetch_cultivos()
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        historial_ciclos = fetch_cycles_by_torre(torre["id_torre"])
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
    except Error as exc:
        flash(f"No se pudieron consultar los cultivos: {exc}", "error")
        cultivos_registrados = []
        ciclo_activo = None
        historial_ciclos = []
        ultima_lectura = None

    return render_template(
        "cultivos.html",
        cultivos=cultivos_registrados,
        ciclo_activo=ciclo_activo,
        historial_ciclos=historial_ciclos,
        torre=torre,
        ultima_lectura=ultima_lectura,
    )


@app.route("/cultivos/nuevo", methods=("GET", "POST"))
@login_required
def crear_cultivo():
    form_data = CultivoFormData()
    if request.method == "POST":
        form_data = CultivoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                insert_cultivo(
                    nombre=form_data.nombre,
                    variedad=form_data.variedad,
                    ubicacion=form_data.ubicacion,
                    estado=form_data.estado,
                    descripcion=form_data.descripcion,
                )
                flash("Cultivo registrado correctamente.", "success")
                return redirect(url_for("cultivos"))
            except Error as exc:
                flash(f"No se pudo guardar el cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")

    return render_template(
        "cultivo_form.html",
        titulo="Nuevo cultivo",
        accion="Guardar cultivo",
        cultivo=form_data,
        errores=form_data.errors,
    )


@app.route("/cultivos/editar/<int:cid>", methods=("GET", "POST"))
@login_required
def editar_cultivo(cid):
    try:
        cultivo = fetch_cultivo(cid)
    except Error as exc:
        flash(f"No se pudo consultar el cultivo: {exc}", "error")
        return redirect(url_for("cultivos"))

    if not cultivo:
        flash("Cultivo no encontrado.", "error")
        return redirect(url_for("cultivos"))

    if request.method == "POST":
        form_data = CultivoFormData.from_request(request.form)
        if form_data.is_valid():
            try:
                update_cultivo(
                    cid,
                    nombre=form_data.nombre,
                    variedad=form_data.variedad,
                    ubicacion=form_data.ubicacion,
                    estado=form_data.estado,
                    descripcion=form_data.descripcion,
                )
                flash("Cultivo actualizado correctamente.", "success")
                return redirect(url_for("cultivos"))
            except Error as exc:
                flash(f"No se pudo actualizar el cultivo: {exc}", "error")
        else:
            flash("Corrige los errores del formulario.", "error")
    else:
        form_data = CultivoFormData.from_mysql_cultivo(cultivo)

    return render_template(
        "cultivo_form.html",
        titulo="Editar cultivo",
        accion="Actualizar cultivo",
        cultivo=form_data,
        errores=form_data.errors,
    )


@app.route("/cultivos/borrar/<int:cid>")
@login_required
def borrar_cultivo(cid):
    try:
        delete_cultivo(cid)
        flash("Cultivo eliminado correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el cultivo: {exc}", "error")
    return redirect(url_for("cultivos"))


@app.route("/sensores")
@login_required
@tower_required
def sensores():
    torre = _current_torre()
    try:
        ciclo_activo = fetch_active_cycle_by_torre(torre["id_torre"])
        ultima_lectura = fetch_latest_sensor_reading_by_torre(torre["id_torre"])
        historial = fetch_sensor_readings_by_torre(torre["id_torre"], 10)
        cultivos_registrados = fetch_cultivos()
    except Error as exc:
        flash(f"No se pudo consultar las lecturas de sensores: {exc}", "error")
        ciclo_activo = None
        ultima_lectura = None
        historial = []
        cultivos_registrados = []

    return render_template(
        "sensores.html",
        ultima_lectura=ultima_lectura,
        historial=historial,
        cultivos=cultivos_registrados,
        ciclo_activo=ciclo_activo,
        torre=torre,
        api_url=url_for("api_sensor_reading"),
    )


@app.route("/api/sensores/lectura", methods=("POST",))
def api_sensor_reading():
    payload = request.get_json(silent=True) or {}

    dispositivo = str(payload.get("dispositivo", "")).strip()
    torre_codigo = str(payload.get("torre_codigo", "")).strip()
    if not dispositivo:
        return jsonify({"ok": False, "error": "El campo 'dispositivo' es obligatorio."}), 400
    if not torre_codigo:
        return jsonify({"ok": False, "error": "El campo 'torre_codigo' es obligatorio."}), 400

    try:
        lectura_id = insert_sensor_reading(
            torre_codigo=torre_codigo,
            dispositivo=dispositivo,
            temperatura_aire=_parse_optional_float(payload.get("temperatura_aire")),
            humedad_aire=_parse_optional_float(payload.get("humedad_aire")),
            temperatura_agua=_parse_optional_float(payload.get("temperatura_agua")),
            ph=_parse_optional_float(payload.get("ph")),
            ec=_parse_optional_float(payload.get("ec")),
            nivel_agua=_parse_optional_float(payload.get("nivel_agua")),
            luminosidad=_parse_optional_float(payload.get("luminosidad")),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Error as exc:
        return jsonify({"ok": False, "error": f"No se pudo guardar la lectura: {exc}"}), 500

    return jsonify({"ok": True, "id_lectura": lectura_id}), 201


@app.route("/planta/<nombre>")
def planta(nombre):
    mensaje = f"Planta: {nombre.capitalize()} registrada en EcoGrow"
    return render_template("planta.html", mensaje=mensaje)


@app.route("/irrigation")
@login_required
def irrigation():
    return render_template("irrigation.html")


@app.route("/demo")
def demo():
    return render_template("demo.html")


@app.route("/sustainability")
@login_required
def sustainability():
    return render_template("sustainability.html")


@app.route("/mysql")
@login_required
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
@login_required
def inicializar_mysql():
    try:
        create_mysql_tables()
        flash("Base de datos MySQL y tablas verificadas correctamente.", "success")
    except Error as exc:
        flash(f"No se pudo inicializar MySQL: {exc}", "error")
    return redirect(url_for("mysql_dashboard"))


@app.route("/mysql/usuarios")
@login_required
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
@login_required
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
@login_required
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
@login_required
def borrar_usuario_mysql(uid):
    try:
        delete_mysql_usuario(uid)
        flash("Usuario eliminado de MySQL.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el usuario: {exc}", "error")
    return redirect(url_for("listar_usuarios_mysql"))


@app.route("/mysql/productos")
@login_required
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
@login_required
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
@login_required
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
@login_required
def borrar_producto_mysql(pid):
    try:
        delete_mysql_producto(pid)
        flash("Producto eliminado de MySQL.", "success")
    except Error as exc:
        flash(f"No se pudo eliminar el producto: {exc}", "error")
    return redirect(url_for("listar_productos_mysql"))


@app.route("/inventario")
@app.route("/productos")
@login_required
def mostrar_inventario():
    productos = inventario.all()
    return render_template("productos.html", productos=productos)


@app.route("/inventario/crear", methods=("GET", "POST"))
@login_required
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
@login_required
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
@login_required
def borrar(pid):
    inventario.delete(pid)
    flash("Producto eliminado de SQLite y archivos sincronizados.", "success")
    return redirect(url_for("mostrar_inventario"))


@app.route("/datos")
@login_required
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


def _parse_optional_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Uno de los valores numericos del sensor no es valido.") from exc


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
