# Pruebas automatizadas

Las pruebas usan `mongomock`, una base MongoDB simulada en memoria. No requieren iniciar MongoDB ni modifican datos reales.

Desde la carpeta raíz del proyecto, activa el entorno virtual e instala las dependencias de desarrollo:

```powershell
pip install -r requirements-dev.txt
```

Ejecuta todas las pruebas:

```powershell
python -m pytest -v
```

Para ejecutar una prueba específica:

```powershell
python -m pytest tests/test_api.py::test_profesor_no_puede_consultar_expediente_de_otro -v
```

Las pruebas cubren registro, inicio de sesión, perfil, validación, expedientes, documentos y aislamiento entre profesores.
