from shiny import ui
import enerhabitat as eh
import os

MAX_CAPAS = 10  # Número máximo de capas por sistema constructivo
MAX_SC = 10  # Número máximo de sistemas constructivos

PRECARGADOS_DIR = "./epw/"

meses = {
    "01": "Enero",
    "02": "Febrero",
    "03": "Marzo",
    "04": "Abril",
    "05": "Mayo",
    "06": "Junio",
    "07": "Julio",
    "08": "Agosto",
    "09": "Septiembre",
    "10": "Octubre",
    "11": "Noviembre",
    "12": "Diciembre",
}

tilt = {"90": "Muro", "0": "Techo"}

azimuth = {
    "0": "Norte",
    "45": "Noreste",
    "90": "Este",
    "135": "Sureste",
    "180": "Sur",
    "225": "Suroeste",
    "270": "Oeste",
    "315": "Noroeste",
}

materiales = eh.get_list_materials()


def init_sistemas():
    """
    Inicializa un diccionario para almacenar los sistemas constructivos y sus capas.
    Cada sistema constructivo comienza con una capa por defecto.
    """
    max_capas = MAX_CAPAS
    max_sc = MAX_SC

    sistemas: dict[int, dict] = {}

    for sc_id in range(1, max_sc + 1):
        sistemas[sc_id] = {
            "absortancia": 0.8,
            "capas_activas": 1,
            "capas": {
                capa_id: {"material": None, "ancho": 0.1}
                for capa_id in range(1, max_capas + 1)
            },
        }
    return sistemas


def side_card():
    return [
        # ui.input_dark_mode(),
        ui.card(
            ui.card_header("Datos cimáticos"),
            ui.input_select(
                id="selector_archivo",
                label="Archivo EPW:",
                choices={
                    **{
                        f"precargado_{archivo}": archivo
                        for i, archivo in enumerate(os.listdir(PRECARGADOS_DIR), 1)
                        if os.path.isfile(os.path.join(PRECARGADOS_DIR, archivo))
                    },
                    **{"upload": " 🗎 Subir archivo"},
                },
                selected=f"precargado_{os.listdir(PRECARGADOS_DIR)[0]}",
            ),
            ui.output_ui("ui_upload"),
            ui.input_select(
                "mes",
                "Mes:",
                meses,
                selected="Enero",
            ),
            ui.input_checkbox("mostrar_Tsa", "Mostrar Tsa", False),
        ),
        ui.card(
            ui.card_header("Datos geométricos"),
            ui.input_select("tilt", "Inclinación:", tilt),
            ui.input_select("azimuth", "Orientación:", azimuth),
        ),
        ui.card(
            ui.card_header("Sistemas constructivos"),
            ui.input_numeric("num_sc", "Número de sistemas:", value=1, min=1, max=MAX_SC, step=1),
            ui.output_ui("ui_sistemas"),
            ui.layout_column_wrap(
                ui.input_action_button(
                    f"remove_capa",
                    "🞬",
                    # width="100%",
                    class_="btn-danger",
                ),
                ui.input_action_button(
                    f"add_capa",
                    "✚",
                    # width="100%",
                    class_="btn-primary",
                ),
                width=1 / 2,
            ),
            ui.input_task_button(
                "resolver_sc",
                "Calcular",
                label_busy="Calculando...",
                width="100%",
                type="success",
            ),
        ),
    ]


def sc_paneles(num_sc, sistemas):
    """
    Crea una lista de paneles de sistemas constructivos para el navset_card_tab.
    """
    paneles = []

    for sc_id in range(1, num_sc + 1):
        # Obtener las capas activas y sus propiedades
        capas_activas = sistemas[sc_id]["capas_activas"]
        capas = sistemas[sc_id]["capas"]

        # Crear elementos del panel del sistema constructivo
        elementos = [
            ui.input_numeric(
                f"absortancia_{sc_id}",
                "Absortancia:",
                value=sistemas[sc_id]["absortancia"],
                min=0,
                max=1,
                step=0.01,
                update_on="blur",
            ),
            ui.h5("Capas:"),
            ui.accordion(
                *capa_paneles(sc_id, capas_activas, capas),
                id=f"capas_accordion_{sc_id}",
                open=f"Capa {capas_activas}",
                multiple=False,
            ),
        ]

        panel = ui.nav_panel(f"SC {sc_id}", elementos)
        paneles.append(panel)

    return paneles


def capa_paneles(sc_id, capas_activas, capas):
    """
    Crea una lista para los elementos del acordeon de las capas activas de un sistema constructivo.
    """
    panels = []
    for capa_id in range(1, capas_activas+1):
        # Asegurarse de que la capa existe en el diccionario de capas
        if capa_id not in capas:
            continue
        
        material = capas[capa_id]["material"]
        ancho = capas[capa_id]["ancho"]
        
        # Crear el panel para la capa
        panels.append(
            ui.accordion_panel(
                f"Capa {capa_id}",
                ui.input_select(
                    f"material_capa_{sc_id}_{capa_id}", "Material:", materiales, selected=material
                ),
                ui.input_numeric(
                    f"ancho_capa_{sc_id}_{capa_id}",
                    "Ancho (m):",
                    value=ancho,
                    step=0.01,
                    min=0.01,
                ),
            )
        )

    return panels
