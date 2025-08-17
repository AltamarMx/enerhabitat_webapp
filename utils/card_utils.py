from shiny import ui, render, reactive
import enerhabitat as eh
import os

from .sistemas import MAX_SC, MAX_CAPAS

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
                ui.card_header("Datos climáticos"),
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
                ui.input_numeric(
                    "num_sc", "Número de sistemas:", value=1, min=1, max=MAX_SC, step=1
                ),
                ui.output_ui("sc_panels"),
                ui.input_task_button(
                    "resolver_sc", "Calcular", label_busy="Calculando...", width="100%",type="success"
                ),
            ),
        ]


def card_server(input, output, session, sistemas):
    # ui de cada panel de SC
    @output
    @render.ui
    def sc_panels():
        num_sc = input.num_sc()
        paneles = [sc_panel(sc_id, sistemas.get()) for sc_id in range(1, num_sc + 1)]
    
        return ui.navset_card_tab(*paneles, id="sc_seleccionado", selected=f"SC {num_sc}")

    

    def sc_panel(sc_id, estado):
        """Genera el panel para un sistema constructivo.

        Parameters
        ----------
        sc_id: int
            Identificador del sistema constructivo.
        estado: dict
            Estado actual de los SC guardado en ``sistemas``.
        """

        sc_info = estado.get(sc_id, {}) if estado else {}
        capas_activas = sc_info.get("capas_activas", [1])
        capas_info = sc_info.get("capas", {})

        elementos = [
            ui.input_numeric(
                f"absortancia_{sc_id}",
                "Absortancia:",
                value=sc_info.get("absortancia", 0.8),
                min=0,
                max=1,
                step=0.01,
                update_on="blur",
            ),
            ui.h5("Capas:"),
            ui.accordion(
                *[
                    capa_panel(sc_id, capa_id, estado)
                    for capa_id in (capas_activas or [1])
                ],
                id=f"capas_accordion_{sc_id}",
                open=f"Capa 1",
                multiple=False,
            ),
            ui.layout_column_wrap(
                ui.input_action_button(
                    f"remove_capa_{sc_id}",
                    "🞬",
                    class_="btn-danger",
                ),
                ui.input_task_button(
                    f"add_capa_{sc_id}",
                    "✚",
                    class_="btn-primary",
                ),
                width=1/2,
            ),
        ]

        return ui.nav_panel(f"SC {sc_id}", elementos)


    def capa_title(capa_id, material=None, ancho=None):
        """Genera el título de la capa con los datos disponibles."""
        if material and ancho is not None:
            return f"Capa {capa_id} - {material} ({ancho} m)"
        return f"Capa {capa_id}"


    def capa_panel(sc_id, capa_id, estado):
        """Panel de una capa específica."""
        capa_info = (
            estado.get(sc_id, {}).get("capas", {}).get(capa_id, {}) if estado else {}
        )
        titulo = capa_title(
            capa_id, capa_info.get("material"), capa_info.get("ancho")
        )

        return ui.accordion_panel(
            titulo,
            ui.input_select(
                f"material_capa_{sc_id}_{capa_id}",
                "Material:",
                materiales,
                selected=capa_info.get("material"),
            ),
            ui.input_numeric(
                f"ancho_capa_{sc_id}_{capa_id}",
                "Ancho (m):",
                value=capa_info.get("ancho", 0.1),
                step=0.01,
                min=0.01,
            ),
        )

    # Contadores y modificación de capas
    capa_counts = {"add": reactive.Value({}), "remove": reactive.Value({})}

    def modify_capa(sc_id, cnt, action):
        """Agregar o remover capas según la acción indicada."""
        with reactive.isolate():
            current = sistemas.get().copy()

        sc = current.setdefault(sc_id, {
            "absortancia": 0.8,
            "capas": {1: {"material": None, "ancho": 0.1}},
            "capas_activas": [1],
        })

        counts = capa_counts[action]
        prev_counts = counts.get()
        activas = sc.get("capas_activas", [])

        if cnt > prev_counts.get(sc_id, 0):
            if action == "add" and len(activas) < MAX_CAPAS:
                siguiente = max(activas) + 1 if activas else 1
                activas.append(siguiente)
                sc["capas_activas"] = activas
                current[sc_id] = sc
                sistemas.set(current)
                ui.insert_accordion_panel(
                    id=f"capas_accordion_{sc_id}",
                    panel=capa_panel(sc_id, siguiente, current),
                )
                ui.update_accordion(
                    id=f"capas_accordion_{sc_id}",
                    show=f"Capa {siguiente}",
                )
            elif action == "remove" and len(activas) > 1:
                eliminado = activas.pop()
                sc["capas_activas"] = activas
                current[sc_id] = sc
                sistemas.set(current)
                ui.update_accordion(
                    id=f"capas_accordion_{sc_id}",
                    show=f"Capa {activas[-1]}",
                )
                ui.remove_accordion_panel(
                    id=f"capas_accordion_{sc_id}",
                    target=f"Capa {eliminado}",
                )

        prev_counts[sc_id] = cnt
        counts.set(prev_counts)

    # Agregar capas
    @reactive.Effect
    def _add_capa():
        with reactive.isolate():
            sc_ids = list(range(1, input.num_sc() + 1))
        for sc_id in sc_ids:
            cnt = input[f"add_capa_{sc_id}"]()
            modify_capa(sc_id, cnt, "add")

    # Eliminar capas
    @reactive.Effect
    def _remove_capa():
        with reactive.isolate():
            sc_ids = list(range(1, input.num_sc() + 1))
        for sc_id in sc_ids:
            cnt = input[f"remove_capa_{sc_id}"]()
            modify_capa(sc_id, cnt, "remove")
            
    # Actualizar títulos de las capas cuando cambien sus datos
    @reactive.Effect
    def _update_capa_titles():
        state = sistemas.get()
        for sc_id in range(1, input.num_sc() + 1):
            sc_info = state.get(sc_id, {})
            for c_id in sc_info.get("capas_activas", []):
                material = input[f"material_capa_{sc_id}_{c_id}"]()
                ancho = input[f"ancho_capa_{sc_id}_{c_id}"]()
                titulo = capa_title(c_id, material, ancho)
                ui.update_accordion_panel(
                    id=f"capas_accordion_{sc_id}",
                    target=f"Capa {c_id}",
                    title=titulo,
                    value=f"Capa {c_id}",
                )
