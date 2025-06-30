from shiny import ui
import enerhabitat as eh
import os

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
            ui.input_numeric("num_sc", "Número de sistemas:", value=1, min=1, step=1),
            ui.output_ui("sc_panels"),
            ui.input_task_button(
                "resolver_sc", "Calcular", label_busy="Calculando...", width="100%",type="success"
            ),
        ),
    ]

def sc_panel(sc_id):
    elementos = [
        ui.input_numeric(
            f"absortancia_{sc_id}",
            "Absortancia:",
            value=0.8,
            min=0,
            max=1,
            step=0.01,
            update_on="blur",
        ),
        ui.h5("Capas:"),
        ui.accordion(
            capa_panel(sc_id, 1),
            id=f"capas_accordion_{sc_id}",
            open=f"Capa 1"
        ),
        ui.layout_column_wrap(
            ui.input_action_button(
                f"remove_capa_{sc_id}",
                "🞬",
                # width="100%",
                class_="btn-danger",
            ),
            ui.input_task_button(
                f"add_capa_{sc_id}",
                "✚",
                # width="100%",
                class_="btn-primary",
            ),
            width=1/2
        ),
    ]

    return ui.nav_panel(f"SC {sc_id}", elementos)

def capa_panel(sc_id, capa_id):
    return ui.accordion_panel(
        f"Capa {capa_id}",
        ui.input_select(
            f"material_capa_{sc_id}_{capa_id}", "Material:", materiales
        ),
        ui.input_numeric(
            f"ancho_capa_{sc_id}_{capa_id}",
            "Ancho (m):",
            value=0.1,
            step=0.01,
            min=0.01,
        )
    )
