from shiny import ui, render, reactive
from .card_utils import PRECARGADOS_DIR
import os

def epw_server(input, output, session, current_file):
    
    # Manejo de EPW's
    @reactive.Effect
    def _():
        # Manejar selección de archivo precargado
        if input.selector_archivo().startswith("precargado_"):
            file_name = input.selector_archivo().replace("precargado_", "", 1)
            file_path = os.path.join(PRECARGADOS_DIR, file_name)
            current_file.set(file_path)

    # Manejar archivo subido
    @reactive.Effect
    def _():
        if input.selector_archivo() == "upload" and input.epw_file() is not None:
            file_info = input.epw_file()[0]
            current_file.set(file_info["datapath"])

    # ui para subir archivo
    @output
    @render.ui
    def ui_upload():
        if input.selector_archivo() == "upload":
            return ui.input_file("epw_file", label="", accept=[".epw"], multiple=False)
        return None
    