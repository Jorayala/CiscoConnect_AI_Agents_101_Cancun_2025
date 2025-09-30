# Cisco MCP Server para APIC e Intersight

Este servidor MCP (Model Context Protocol) proporciona herramientas para interactuar con Cisco APIC (Application Policy Infrastructure Controller) y Cisco Intersight a través de Claude Desktop.

## 🚀 Características

### Herramientas de Cisco APIC
- **fetch_apic_class**: Obtiene clases de objetos administrados de APIC
- **create_tenant**: Crea nuevos tenants en APIC
- **create_vrf**: Crea VRFs (Virtual Routing and Forwarding) en tenants
- **create_bridge_domain**: Crea Bridge Domains asociados a VRFs
- **make_aci_backup**: Configura backups automáticos de APIC

### Herramientas de Cisco Intersight
- **get_intersight_servers**: Obtiene lista de servidores físicos
- **get_intersight_organizations**: Obtiene organizaciones de Intersight
- **get_intersight_alarms**: Obtiene alarmas activas
- **create_intersight_server_profile**: Crea perfiles de servidor
- **get_intersight_hyperflex_clusters**: Obtiene información de clusters HyperFlex

## 📋 Requisitos Previos

- Python 3.8 o superior
- Acceso a Cisco APIC
- Acceso a Cisco Intersight
- Claude Desktop configurado

## 🛠️ Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/Jorayala/CiscoConnect_AI_Agents_101_Cancun_2025.git
   cd CiscoConnect_AI_Agents_101_Cancun_2025/MCP_Server
   ```

2. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura las variables de entorno:**
   ```bash
   cp env.template .env
   # Edita el archivo .env con tus credenciales
   ```

## ⚙️ Configuración

### Variables de Entorno Requeridas

#### Para Cisco APIC:
```bash
APIC_BASE_URL=https://your-apic-ip-address
APIC_USERNAME=your-apic-username
APIC_PASSWORD=your-apic-password
```

#### Para Cisco Intersight:
```bash
INTERSIGHT_BASE_URL=https://intersight.com
INTERSIGHT_API_KEY=your-intersight-api-key-id
INTERSIGHT_SECRET_KEY="-----BEGIN RSA PRIVATE KEY-----
YOUR_PRIVATE_KEY_CONTENT_HERE
-----END RSA PRIVATE KEY-----"
```

### Configuración de Claude Desktop

Agrega la siguiente configuración a tu archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cisco-apic-intersight": {
      "command": "python",
      "args": ["/ruta/completa/al/MCP_Server/main.py"],
      "env": {
        "APIC_BASE_URL": "https://your-apic-ip",
        "APIC_USERNAME": "your-username",
        "APIC_PASSWORD": "your-password",
        "INTERSIGHT_BASE_URL": "https://intersight.com",
        "INTERSIGHT_API_KEY": "your-api-key",
        "INTERSIGHT_SECRET_KEY": "your-private-key"
      }
    }
  }
}
```

## 🚀 Uso

Una vez configurado, puedes usar las herramientas directamente en Claude Desktop:

### Ejemplos de Uso:

**Obtener información de tenants:**
```
Obtén la lista de tenants del APIC
```

**Crear un nuevo tenant:**
```
Crea un tenant llamado "mi-tenant" con descripción "Tenant de prueba"
```

**Obtener servidores de Intersight:**
```
Muestra los servidores físicos registrados en Intersight
```

**Crear un perfil de servidor:**
```
Crea un perfil de servidor llamado "mi-perfil" en la organización "default"
```

## 🔒 Seguridad

- **Nunca** commits el archivo `.env` al repositorio
- Usa variables de entorno para todas las credenciales
- Mantén tus claves privadas seguras
- Considera usar certificados SSL válidos en producción

## 🐛 Solución de Problemas

### Error de Autenticación APIC
- Verifica que las credenciales sean correctas
- Asegúrate de que el APIC sea accesible desde tu red
- Revisa los logs para más detalles

### Error de Autenticación Intersight
- Verifica que la API key sea válida
- Asegúrate de que la clave privada esté correctamente formateada
- Verifica que el formato de la clave privada sea PEM

### Problemas de Conexión
- Verifica la conectividad de red
- Revisa los firewalls y proxies
- Asegúrate de que los certificados SSL sean válidos

## 📝 Logs

El servidor genera logs detallados que incluyen:
- Información de autenticación
- Errores de API
- Estado de las operaciones

Los logs se muestran en la consola donde se ejecuta el servidor.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Para soporte técnico o preguntas:
- Abre un issue en GitHub
- Contacta al equipo de desarrollo
- Revisa la documentación de Cisco APIC e Intersight

---

**Nota**: Este servidor MCP está diseñado para uso en entornos de desarrollo y testing. Para uso en producción, considera implementar medidas de seguridad adicionales.
