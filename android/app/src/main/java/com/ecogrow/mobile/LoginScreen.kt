package com.ecogrow.mobile

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun LoginScreen(
    busy: Boolean,
    errorMessage: String?,
    onLogin: (mail: String, pass: String) -> Unit,
    onRegister: (name: String, mail: String, pass: String, passConfirm: String) -> Unit
) {
    var isRegisterMode by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var mail by remember { mutableStateOf("") }
    var pass by remember { mutableStateOf("") }
    var passConfirm by remember { mutableStateOf("") }
    var localValidationErr by remember { mutableStateOf<String?>(null) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF7FAF7))
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(28.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Logo de marca oficial EcoGrow
                Image(
                    painter = painterResource(R.drawable.ecogrow_symbol),
                    contentDescription = "Logo EcoGrow",
                    modifier = Modifier.size(72.dp)
                )

                Text(
                    text = "EcoGrow",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF195C3D)
                )

                Text(
                    text = if (isRegisterMode) "Crea tu cuenta de operador para gestionar tus torres"
                           else "Sistema de Gestión y Control Hidropónico Remoto",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color(0xFF666666),
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(2.dp))

                val displayError = localValidationErr ?: errorMessage
                if (!displayError.isNullOrBlank()) {
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = Color(0xFFFFEBEE),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = displayError,
                            color = Color(0xFFB3261E),
                            fontSize = 13.sp,
                            modifier = Modifier.padding(12.dp),
                            textAlign = TextAlign.Center
                        )
                    }
                }

                if (isRegisterMode) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it; localValidationErr = null },
                        label = { Text("Nombre Completo") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    )
                }

                OutlinedTextField(
                    value = mail,
                    onValueChange = { mail = it; localValidationErr = null },
                    label = { Text("Correo Electrónico") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                )

                OutlinedTextField(
                    value = pass,
                    onValueChange = { pass = it; localValidationErr = null },
                    label = { Text(if (isRegisterMode) "Contraseña (mínimo 8 caracteres)" else "Contraseña") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                )

                if (isRegisterMode) {
                    OutlinedTextField(
                        value = passConfirm,
                        onValueChange = { passConfirm = it; localValidationErr = null },
                        label = { Text("Confirmar Contraseña") },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    )
                }

                Button(
                    onClick = {
                        localValidationErr = null
                        if (isRegisterMode) {
                            if (name.isBlank() || mail.isBlank() || pass.isBlank()) {
                                localValidationErr = "Completa todos los campos requeridos."
                                return@Button
                            }
                            if (pass.length < 8) {
                                localValidationErr = "La contraseña debe tener al menos 8 caracteres."
                                return@Button
                            }
                            if (pass != passConfirm) {
                                localValidationErr = "Las contraseñas no coinciden."
                                return@Button
                            }
                            onRegister(name, mail, pass, passConfirm)
                        } else {
                            if (mail.isBlank() || pass.isBlank()) {
                                localValidationErr = "Indica correo y contraseña."
                                return@Button
                            }
                            onLogin(mail, pass)
                        }
                    },
                    enabled = !busy,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                ) {
                    if (busy) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(22.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text(
                            text = if (isRegisterMode) "Crear Cuenta" else "Iniciar Sesión",
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp
                        )
                    }
                }

                TextButton(
                    onClick = {
                        isRegisterMode = !isRegisterMode
                        localValidationErr = null
                    }
                ) {
                    Text(
                        text = if (isRegisterMode) "¿Ya tienes cuenta? Inicia sesión"
                               else "¿No tienes una cuenta? Regístrate aquí",
                        color = Color(0xFF087F8C),
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 13.sp
                    )
                }
            }
        }
    }
}
