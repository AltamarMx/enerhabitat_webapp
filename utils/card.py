from shiny import ui
import enerhabitat as eh
import os

PRECARGADOS_DIR="./epw/"

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
    "0":"Norte",
    "45":"Noroeste",
    "90":"Oeste",
    "135":"Suroeste",
    "180":"Sur",
    "225":"Sureste",
    "270":"Este",
    "315":"Noreste",
}

materiales = eh.get_list_materials()


def panel_card(num):
    return ui.nav_panel(
        f"SC {num}",
        ui.h4("Datos climáticos"),
        ui.input_select(
                id="selector_archivo",
                label="Archivo EPW:",
                choices={
                    **{f"precargado_{archivo}": archivo 
                        for i, archivo in enumerate(os.listdir(PRECARGADOS_DIR), 1) 
                            if os.path.isfile(os.path.join(PRECARGADOS_DIR, archivo))},
                    **{"upload": "↪ Subir mi propio archivo"}
                }
            ),
        ui.output_ui("ui_upload"),
        ui.input_select("mes", "Mes:", meses, selected="Enero",),
        ui.hr(),
        ui.h4("Parámetros geométricos"),
        ui.input_select("tilt", "Inclinación:", tilt),
        ui.input_select("azimuth", "Orientación:", azimuth),
        ui.hr(),
        ui.h4("Sistema constructivo"),
        ui.input_select('material_capa_1', "Material:",materiales),
        ui.input_numeric("ancho_capa_1", "Ancho (mm):",value=0.01,step=0.01,min=0.01),
        ui.input_numeric("absortancia", "Absortancia:",value=0.8,min=0, max=1)
    )

