import tkinter as tk
from tkinter.font import Font
from time import sleep
from threading import Thread
from threading import Event
import threading
import subprocess
import os
from tkinter import messagebox
import configparser
import sys

RUTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
MAIN_DIR = os.path.dirname(os.path.abspath(sys.executable))
ICON_DIR = os.path.join(RUTA_SCRIPT, "icono")
ICON = os.path.join(ICON_DIR, "icon_89.ico")
CONFIG_FILE = os.path.join(MAIN_DIR, "config.ini")
INSTRUCTIONS_FILE = os.path.join(MAIN_DIR, "instrucciones.txt")

class Timer(tk.Frame):
    def __init__(self, parent):
        # --- Load Configuration ---
        self.config_settings = self._load_config() # Store all settings here
        self.colors = self.config_settings['colors'] # Extract colors
        self.shutdown_warning_enabled = self.config_settings['shutdown_warning_enabled'] # Extract warning flag
        
        tk.Frame.__init__(self, parent, bg=self.colors['bg_dark'])
        self.root = parent
        self.active = False
        self.kill = False
        self.start_hours = tk.StringVar(value=0)
        self.start_minutes = tk.StringVar(value=0)
        self.start_seconds = tk.StringVar(value=0)
        self.start_hours.trace("w", self.remove_alpha)
        self.start_minutes.trace("w", self.remove_alpha)
        self.start_seconds.trace("w", self.remove_alpha)
        self.hours_left = 0
        self.minutes_left = 0
        self.seconds_left = 0
        self.time_remaining = "00:00:00"
        self.clock = None
        self.cancelar_cierre = False
        self.salir = None
        self.show_title = True
        self.siempre_en_primer_plano = True
        self.tiempo_espera = 15  # Tiempo de espera en segundos

        # Crear la interfaz en tema oscuro
        # Define el tamaño de la fuente
        self.spinbox_frame = tk.Frame(self, bg=self.colors['bg_dark'])
        self.hours_frame = tk.LabelFrame(self.spinbox_frame, text="Horas:", fg=self.colors['clock_color_normal'], bg=self.colors['bg_lighter'])
        self.hours_select = tk.Spinbox(self.hours_frame, from_=0, to=99, width=2, textvariable=self.start_hours, 
                                       font=Font(family='Helvetica', size=34, weight='bold'),
                                       bg=self.colors['bg_dark'], fg=self.colors['spinbox_text_color'])
        self.minutes_frame = tk.LabelFrame(self.spinbox_frame, text="Minutos:", fg=self.colors['clock_color_normal'], bg=self.colors['bg_lighter'])
        self.minutes_select = tk.Spinbox(self.minutes_frame, from_=0, to=59, textvariable=self.start_minutes,
                                         font=Font(family='Helvetica', size=34, weight='bold'),
                                         width=2, bg=self.colors['bg_dark'], fg=self.colors['spinbox_text_color'])
        self.seconds_frame = tk.LabelFrame(self.spinbox_frame, text="Segundos:", fg=self.colors['clock_color_normal'], bg=self.colors['bg_lighter'])
        self.seconds_select = tk.Spinbox(self.seconds_frame, from_=0, to=59, textvariable=self.start_seconds,
                                         font=Font(family='Helvetica', size=34, weight='bold'),
                                         width=2, bg=self.colors['bg_dark'], fg=self.colors['spinbox_text_color'])

        self.button_frame = tk.Frame(self, bg=self.colors['bg_dark'])
        self.active_button = tk.Button(self.button_frame, text="Iniciar", command=self.start, bg=self.colors['button_color'], fg=self.colors['clock_color_normal'], relief="raised", anchor="center", activebackground=self.colors['button_active_color'])
        self.stop_button = tk.Button(self.button_frame, text="Cancelar", command=self.stop, bg=self.colors['button_color'], fg=self.colors['clock_color_normal'], relief="raised", anchor="center", activebackground=self.colors['button_active_color'])
        self.pause_button = tk.Button(self.button_frame, text="  Pausar   ", command=self.pause, bg=self.colors['button_color'], fg=self.colors['clock_color_normal'], relief="raised", anchor="center", activebackground=self.colors['button_active_color'])
        self.cuenta_regresiva_label = tk.Label(self, font=("Helvetica"), fg=self.colors['clock_color_red'], bg=self.colors['bg_dark'])
        self.cancelar_apagado_boton = tk.Button(self, bg=self.colors['button_color'], fg=self.colors['clock_color_normal'], relief="raised", anchor="center", activebackground=self.colors['button_active_color'])

        # Organiza los widgets de forma fija
        self.spinbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=5)
        self.hours_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.minutes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.seconds_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.hours_select.pack(fill=tk.BOTH, expand=4)
        self.minutes_select.pack(fill=tk.BOTH, expand=4)
        self.seconds_select.pack(fill=tk.BOTH, expand=4)

        self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        self.active_button.pack(fill=tk.BOTH, expand=1)

        self.update_event = Event()  # Evento para pausar el hilo de actualización
        self.thread = Thread(target=self.update, daemon=True)
        self.thread.start()  # Solo iniciamos el hilo una vez aquí en el constructor
        self.resize_delay = None
        self.root.bind("<Configure>", self.on_resize)
        self.last_height = 1
        # Agregar funcionalidad de ajustar la transparencia de la ventana
        self.root.bind("<Control-Up>", self.adjust_transparency)
        self.root.bind("<Control-Down>", self.adjust_transparency)
        self.root.bind("<Control-t>", self.toggle_title_bar)
        self.root.bind("<Control-T>", self.toggle_title_bar)
        self.root.bind("<Control-f>", self.handle_configuracion)
        self.root.bind("<Control-F>", self.handle_configuracion)
        # Agregar funcionalidad de mover ventana
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        # resize
        self.root.bind("<ButtonPress-3>", self.start_resize)
        self.root.bind("<B3-Motion>", self.do_resize)
        self.root.bind("<ButtonRelease-3>", self.stop_resize)
        self._create_instructions_file()

    def _load_config(self):
        """Loads configuration from config.ini or creates a default."""
        config = configparser.ConfigParser()
        
        # Default color settings
        default_colors = {
            'bg_dark': "#2e2e2e",
            'bg_lighter': "#363636",
            'button_color': "#0b7abd",
            'button_active_color': "#57c0ff",
            'spinbox_text_color': "#1188d1",
            'clock_color_normal': "white",
            'clock_color_orange': "orange",
            'clock_color_red': "red",
            'warning_message_color': "#9b111e", # Color for the shutdown warning popup
            'cancel_button_color': "#9c0b0b", # Color for the cancel shutdown button
            'cancel_success_color': "#2ec248" # Color for cancellation success popup
        }
        
        # Default general settings
        default_settings = {
            'shutdown_warning_enabled': "True" # Stored as string, convert to bool
        }

        # Combine for initial config object if file doesn't exist
        full_config = configparser.ConfigParser()
        full_config['Colors'] = default_colors
        full_config['Settings'] = default_settings

        if os.path.exists(CONFIG_FILE):
            try:
                config.read(CONFIG_FILE)
                # Overwrite defaults with values from file
                if 'Colors' in config:
                    for key in default_colors:
                        default_colors[key] = config['Colors'].get(key, default_colors[key])
                if 'Settings' in config:
                    for key in default_settings:
                        default_settings[key] = config['Settings'].get(key, default_settings[key])
            except Exception as e:
                messagebox.showwarning("Error de Configuración", f"Error al leer config.ini: {e}. Usando valores por defecto.")
        else:
            # Create default config file if it doesn't exist
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    full_config.write(f)
            except Exception as e:
                messagebox.showwarning("Error de Archivo", f"No se pudo crear config.ini: {e}. Continuará sin archivo de configuración.")
        
        # Return parsed settings, converting types as needed
        return {
            'colors': default_colors,
            'shutdown_warning_enabled': default_settings['shutdown_warning_enabled'].lower() == 'true'
        }

    # Función para manejar la configuración de "Siempre en Primer Plano"
    def handle_configuracion(self, event=None): # Añadir el parámetro event
        self.siempre_en_primer_plano = not self.siempre_en_primer_plano
        if self.siempre_en_primer_plano:
            self.root.wm_attributes("-topmost", 1)
        else:
            self.root.wm_attributes("-topmost", 0)
        
    # Función para mostrar/ocultar la barra de título
    def toggle_title_bar(self, event=None):
        self.show_title = not self.show_title
        root.overrideredirect(not self.show_title)
    
    def adjust_transparency(self, event):
        current_alpha = self.root.attributes("-alpha")
        step = 0.01  # Ajuste más preciso para la transparencia
        if event.keysym == "Up":
            self.root.attributes("-alpha", min(current_alpha + step, 1.0))
        elif event.keysym == "Down":
            self.root.attributes("-alpha", max(current_alpha - step, 0.2))

    def start_move(self, event):
        self.x_offset = event.x_root
        self.y_offset = event.y_root

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x_root - self.x_offset)
        y = self.root.winfo_y() + (event.y_root - self.y_offset)
        self.root.geometry(f"+{x}+{y}")
        self.x_offset = event.x_root
        self.y_offset = event.y_root

    def on_resize(self, event):
        if self.resize_delay:
            self.root.after_cancel(self.resize_delay)
        self.resize_delay = self.root.after(55, self.update_text_size)

    def update_text_size(self, event=None):
        """Actualiza el tamaño del texto según el tamaño actual de la ventana."""
        current_height = self.root.winfo_height()
        if abs(current_height - self.last_height) < 5:  # Evita redimensionar si el cambio es menor a 5 px
            return
        
        font_size_buttons = max(10, min(53, int(current_height / 14)))
        font_size_spin = max(28, min(220, int(current_height / 7)))
        font_size_text = max(10, min(50, int(current_height / 23)))
        
        # Aplica los nuevos tamaños de fuente a los elementos
        self.active_button.config(font=Font(family='Helvetica', size=font_size_buttons, weight='bold'))

        self.hours_frame.config(font=Font(family='Helvetica', size=font_size_text))
        self.minutes_frame.config(font=Font(family='Helvetica', size=font_size_text))
        self.seconds_frame.config(font=Font(family='Helvetica', size=font_size_text))

        self.hours_select.config(font=Font(family='Helvetica', size=font_size_spin, weight='bold'))
        self.minutes_select.config(font=Font(family='Helvetica', size=font_size_spin, weight='bold'))
        self.seconds_select.config(font=Font(family='Helvetica', size=font_size_spin, weight='bold'))
        self.cuenta_regresiva_label.config(font=Font(family='Helvetica', size=font_size_spin, weight='bold'))
        self.cancelar_apagado_boton.config(font=Font(family='Helvetica', size=font_size_buttons, weight='bold'))
        
        if self.clock is not None:
            font_size_clock = max(47, min(227, int(current_height / 4)))
            self.clock.config(font=Font(family='Helvetica', size=font_size_clock, weight='bold'))
            self.pause_button.config(font=Font(family='Helvetica', size=font_size_buttons, weight='bold'))
            self.stop_button.config(font=Font(family='Helvetica', size=font_size_buttons, weight='bold'))
        
        # Almacena la altura actual
        self.last_height = current_height

    def remove_alpha(self, var, index, mode):
        current = str(self.start_hours.get())
        self.start_hours.set("".join(x for x in current if x.isdigit()))
        if current == "":
            self.start_hours.set(0)
        current = str(self.start_minutes.get())
        self.start_minutes.set("".join(x for x in current if x.isdigit()))
        if current == "":
            self.start_minutes.set(0)
        elif int(current) > 59:
            self.start_minutes.set(59)
        current = str(self.start_seconds.get())
        self.start_seconds.set("".join(x for x in current if x.isdigit()))
        if current == "":
            self.start_seconds.set(0)
        elif int(current) > 59:
            self.start_seconds.set(59)

    def update(self):
        """Mantiene el temporizador actualizado solo cuando `self.active` es `True`."""
        while not self.kill:
            # Espera a que se active el evento de actualización
            self.update_event.wait()
            
            if self.active and self.clock is not None:
                if self.hours_left + self.minutes_left + self.seconds_left != 0:
                    self.update_clock()
                    sleep(1)
                    if self.seconds_left > 0:
                        self.seconds_left -= 1
                    elif self.minutes_left > 0:
                        self.seconds_left = 59
                        self.minutes_left -= 1
                    elif self.hours_left > 0:
                        self.minutes_left = 59
                        self.hours_left -= 1
                else:
                    self.timer_end()
            else:
                sleep(1)

    def update_clock(self):
        if self.clock:
            hours = f"{self.hours_left:02}"
            minutes = f"{self.minutes_left:02}"
            seconds = f"{self.seconds_left:02}"
            self.time_remaining = f"{hours}:{minutes}:{seconds}"
            self.clock.config(text=self.time_remaining)

            # Cambiar el color de acuerdo al tiempo restante
            total_seconds = self.hours_left * 3600 + self.minutes_left * 60 + self.seconds_left
            if total_seconds <= 29:
                self.clock.config(fg=self.colors['clock_color_red'])
            elif total_seconds <= 59:
                self.clock.config(fg=self.colors['clock_color_orange'])
            else:
                self.clock.config(fg=self.colors['clock_color_normal'])

    def show_timed_message(self, title, message, duration=15000, color="#9b111e"):
        """Muestra una ventana de mensaje personalizada que se cierra automáticamente después de `duration` milisegundos."""
        # Crea una nueva ventana para el mensaje
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)  # Elimina el borde de la ventana
        popup.attributes('-alpha', 0.78)  # Define transparencia
        popup.attributes('-topmost', True)  # Mantiene la ventana en primer plano
        popup.configure(bg=color)  # Fondo de color rojo oscuro

        # Define el tamaño de la ventana emergente
        popup_width = 390
        popup_height = 150

        # Obtiene el ancho y alto de la pantalla
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()

        # Calcula las coordenadas para centrar el popup
        x_position = (screen_width - popup_width) // 2
        y_position = (screen_height - popup_height) // 2

        # Aplica las coordenadas calculadas
        popup.geometry(f"{popup_width}x{popup_height}+{x_position}+{y_position}")

        # Añade el mensaje personalizado
        label = tk.Label(
            popup,
            text=message,
            fg="white",               # Texto en blanco
            bg=color,
            font=("Helvetica", 19, "bold"),  # Fuente más grande y negrita
            wraplength=320,           # Ajuste de línea en 320 píxeles
            justify="center"          # Alineación centrada
        )
        label.pack(expand=True, fill="both", padx=10, pady=10)

        # Programa el cierre automático de la ventana después del tiempo especificado
        self.root.after(duration, popup.destroy)

    def timer_end(self):
        self.active = False
        self.time_remaining = "00:00:00"
        self.clock.config(text=self.time_remaining, fg=self.colors['clock_color_red'])

        if self.shutdown_warning_enabled:
            self.show_timed_message("Apagado en proceso", "El sistema se apagará en 60 segundos. Guarda tu trabajo.", 4700)

            # Mostrar una cuenta regresiva grande en la interfaz
            self.cuenta_regresiva_label.config(font=Font(family='Helvetica', weight='bold'))
            
            self.actualizar_cuenta_regresiva(self.tiempo_espera)

            # Programar el cierre de la aplicación (con precaución)
            self.cancelar_cierre = False
            self.cierre_programado = self.root.after(15000, self.cerrar_aplicacion)

            # Cambiar la interfaz para permitir cancelar el apagado
            self.clock.pack_forget()
            self.pause_button.pack_forget()
            self.stop_button.pack_forget()
            self.button_frame.pack_forget()
            self.cancelar_apagado_boton.config(font=Font(family='Helvetica', weight='bold'))
            self.cancelar_apagado_boton.config(
                text="Cancelar Apagado",
                command=self.cancelar_apagado,
                bg=self.colors['cancel_button_color'],
                fg="white",
                relief="solid",
                anchor="center"
            )
            self.cuenta_regresiva_label.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            self.cancelar_apagado_boton.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=3)
            self.last_height += 1969
            self.update_text_size()
        else:
            self.cancelar_cierre = False
            self.cuenta_regresiva = 1
            self.cierre_programado = self.root.after(1000, self.cerrar_aplicacion)
            self.clock.pack_forget()
            self.pause_button.pack_forget()
            self.stop_button.pack_forget()
            self.button_frame.pack_forget()
            self.cancelar_apagado_boton.config(font=Font(family='Helvetica', weight='bold'))
            self.cancelar_apagado_boton.config(
                text="Cancelar Apagado",
                command=self.cancelar_apagado,
                bg=self.colors['cancel_button_color'],
                fg="white",
                relief="solid",
                anchor="center"
            )
            self.cancelar_apagado_boton.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=5)
            self.last_height += 1969
            self.update_text_size()

    def actualizar_cuenta_regresiva(self, tiempo_restante):
        if tiempo_restante >= 0:
            self.cuenta_regresiva_label.config(text=str(tiempo_restante))
            self.cuenta_regresiva = self.root.after(1000, self.actualizar_cuenta_regresiva, tiempo_restante - 1)
        else:
            self.cuenta_regresiva_label.pack_forget()
            self.last_height += 6969
            self.update_text_size()
     
    def cancelar_apagado(self):
        # Cancelar el apagado automático del sistema
        subprocess.run(["shutdown", "/a"])
        if self.salir:
            self.root.after_cancel(self.salir)
            self.salir = None
        self.cancelar_apagado_boton.pack_forget()
        if self.cuenta_regresiva_label:
            if self.cuenta_regresiva:
                self.root.after_cancel(self.cuenta_regresiva)
                self.cuenta_regresiva = None
            self.cuenta_regresiva_label.pack_forget()
        self.show_timed_message("Apagado Automático", "Apagado Automático cancelado.", 3650, self.colors['cancel_success_color'])

        # Establecer la variable para cancelar el cierre de la aplicación
        self.cancelar_cierre = True
        if self.cierre_programado:
            self.root.after_cancel(self.cierre_programado)  # Cancela el cierre programado de la aplicación
            self.cierre_programado = None
        self.reset_interface()
    
    def cerrar_aplicacion(self):
        # Solo cierra la aplicación si no se ha cancelado el apagado
        if not self.cancelar_cierre:
            comando = ["shutdown", "/s", "/t", "60", "/c", '"El sistema se apagará en 60 segundos. Guarda tu trabajo."']
            subprocess.run(comando)
            self.salir = self.root.after(60000, self.root.destroy)
    
    def reset_interface(self):
        """Restablece la interfaz a su estado inicial."""
        self.clock.pack_forget()
        self.spinbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=5)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        self.active_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.pause_button.pack_forget()
        self.stop_button.pack_forget()
        self.active_button.config(text="Iniciar", command=self.start, bg=self.colors['button_color'], fg=self.colors['clock_color_normal'], relief="raised", anchor="center")
        self.start_hours.set(0)
        self.start_minutes.set(0)
        self.start_seconds.set(0)
        self.last_height = 9999
        self.update_text_size()
        root.overrideredirect(False)

    def toggle_buttons(self, event=None):
        # Verifica el texto del botón "Pausar" y si el botón "Cancelar" está visible
        if self.pause_button.cget("text") == "  Pausar   " and self.stop_button.winfo_ismapped():
            # Oculta los botones y el marco que los contiene
            self.pause_button.pack_forget()
            self.stop_button.pack_forget()
            self.button_frame.pack_forget()  # Oculta el marco de botones
            self.clock.pack(side=tk.TOP, fill=tk.BOTH, expand=1)  # El reloj ocupa toda la ventana
        else:
            # Muestra el marco de botones y ajusta el reloj
            self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
            self.stop_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
            self.pause_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
            self.clock.pack(side=tk.TOP, fill=tk.BOTH, expand=3)  # Ajusta el reloj

    def start(self):
        if int(self.start_hours.get()) == 0 and int(self.start_minutes.get()) == 0 and int(self.start_seconds.get()) == 0:
            return

        # Establece el tiempo restante
        self.hours_left = int(self.start_hours.get())
        self.minutes_left = int(self.start_minutes.get())
        self.seconds_left = int(self.start_seconds.get())
        
        # Oculta el selector de tiempo y muestra el reloj
        self.spinbox_frame.pack_forget()
        self.active_button.pack_forget()
        self.button_frame.pack_forget()  # Oculta también el marco de botones si está visible
        self.clock = tk.Label(self, text=self.time_remaining, font=Font(family='Helvetica', size=36, weight='bold'), bg="#2e2e2e", fg=self.colors['clock_color_normal'])
        self.clock.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Enlazar el evento de doble clic al reloj
        self.clock.bind("<Double-Button-1>", self.toggle_buttons)
        self.pause_button.config(text="  Pausar   ", command=self.pause)
        self.last_height += 1997
        root.overrideredirect(True)
        self.update_text_size()
       
        # Inicia el temporizador
        self.update_event.set()  # Inicia o reanuda el hilo de actualización
        self.active = True
    
    def pause(self):
        self.active = False
        self.update_event.clear()  # Pausa el hilo de actualización
        self.pause_button.config(text="Reanudar", command=self.resume)

    def resume(self):
        self.active = True
        self.update_event.set()  # Reanuda el hilo de actualización
        self.pause_button.config(text="  Pausar   ", command=self.pause)
        self.toggle_buttons()

    def stop(self):
        response = messagebox.askyesno("Confirmación", "¿Estás seguro de que deseas cancelar?")
        if response:
            self.active = False
            self.update_event.clear()  # Detiene el hilo de actualización
            self.reset_interface()  # Restaura la interfaz

            # Muestra el selector de tiempo nuevamente y solo el botón "Iniciar"
            self.spinbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            self.stop_button.pack_forget()  # Oculta el botón "Cancelar"
            self.active_button.config(text="Iniciar", command=self.start)
        
    def start_resize(self, event):
        """
        Registra la posición inicial y determina la esquina desde la que se inicia el redimensionamiento.
        """
        margin = 25
        self.start_x = event.x_root
        self.start_y = event.y_root

        # Posición y tamaño actual de la ventana
        self.win_x = self.root.winfo_x()
        self.win_y = self.root.winfo_y()
        self.win_width = self.root.winfo_width()
        self.win_height = self.root.winfo_height()

        # Determina la esquina según la posición del cursor
        if event.x <= margin and event.y <= margin:
            self.resize_corner = "top_left"
        elif event.x >= self.win_width - margin and event.y <= margin:
            self.resize_corner = "top_right"
        elif event.x <= margin and event.y >= self.win_height - margin:
            self.resize_corner = "bottom_left"
        elif event.x >= self.win_width - margin and event.y >= self.win_height - margin:
            self.resize_corner = "bottom_right"
        else:
            self.resize_corner = None

    def do_resize(self, event):
        """
        Realiza el redimensionamiento según la esquina detectada.
        """
        if not self.resize_corner:
            return

        dx = event.x_root - self.start_x
        dy = event.y_root - self.start_y

        min_width = 160
        min_height = 120

        if self.resize_corner == "bottom_right":
            new_width = max(self.win_width + dx, min_width)
            new_height = max(self.win_height + dy, min_height)
            new_x = self.win_x
            new_y = self.win_y
        elif self.resize_corner == "top_left":
            new_width = max(self.win_width - dx, min_width)
            new_height = max(self.win_height - dy, min_height)
            new_x = self.win_x + dx
            new_y = self.win_y + dy
        elif self.resize_corner == "top_right":
            new_width = max(self.win_width + dx, min_width)
            new_height = max(self.win_height - dy, min_height)
            new_x = self.win_x
            new_y = self.win_y + dy
        elif self.resize_corner == "bottom_left":
            new_width = max(self.win_width - dx, min_width)
            new_height = max(self.win_height + dy, min_height)
            new_x = self.win_x + dx
            new_y = self.win_y

        # Actualiza la geometría de la ventana (incluyendo posición)
        self.root.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")

    def stop_resize(self, event):
        """
        Finaliza el proceso de redimensionamiento.
        """
        self.resize_corner = None

    def _create_instructions_file(self):
        """Creates the instructions.txt file if it doesn't exist."""
        if not os.path.exists(INSTRUCTIONS_FILE):
            try:
                with open(INSTRUCTIONS_FILE, 'w', encoding='utf-8') as f:
                    f.write("""
###################################################
#            INSTRUCCIONES DE USO                 #
#          Apagado Automático Personalizable      #
###################################################

¡Bienvenido al Apagado Automático Personalizable!

Este programa es un temporizador de cuenta regresiva que apagará tu sistema al finalizar, con opciones de personalización.

---

1.  FUNCIONAMIENTO BÁSICO

    * AJUSTAR TIEMPO:
        * Al iniciar, verás tres campos (Horas, Minutos, Segundos). Usa las flechas arriba/abajo o escribe directamente los números para establecer el tiempo deseado para el apagado.
        * El sistema validará automáticamente que los valores sean números y estén dentro de rangos lógicos (0-99 para horas, 0-59 para minutos/segundos).

    * INICIAR:
        * Haz clic en el botón "Iniciar" para comenzar la cuenta regresiva.
        * La ventana cambiará a un modo compacto sin barra de título, mostrando solo el tiempo.

    * PAUSAR / REANUDAR:
        * Una vez iniciado, haz doble clic en el reloj (donde se muestra el tiempo) para revelar los botones "Pausar" y "Cancelar".
        * Haz clic en "Pausar" para detener temporalmente la cuenta. El botón cambiará a "Reanudar".
        * Haz clic en "Reanudar" para continuar la cuenta.
        * Haz doble clic en el reloj nuevamente para ocultar los botones si no los necesitas a la vista.

    * CANCELAR:
        * Haz clic en "Cancelar" para detener el temporizador y regresar a la pantalla de configuración inicial. Se te pedirá confirmación.

    * FIN DEL TEMPORIZADOR (APAGADO):
        * Cuando el tiempo llega a cero, el reloj se pondrá en rojo.
        * **Si `SHUTDOWN_WARNING_ENABLED` está en `True` (ver `config.ini`):**
            * Aparecerá una ventana de aviso y una cuenta regresiva de 15 segundos en la interfaz.
            * Durante esos 15 segundos, tienes la opción de hacer clic en el botón **"Cancelar Apagado"** para detener el proceso de apagado del sistema y volver a la interfaz inicial.
            * Si no se cancela, el sistema se apagará 60 segundos después de finalizar el temporizador (dando tiempo adicional para guardar).
        * **Si `SHUTDOWN_WARNING_ENABLED` está en `False`:**
            * El sistema se apagará automáticamente 60 segundos después de finalizar el temporizador, sin aviso previo en pantalla ni opción de cancelar desde la interfaz del programa.

---

2.  CONFIGURACIÓN DE COLORES Y AJUSTES (config.ini)

    Puedes personalizar los colores de la interfaz y algunos ajustes del temporizador editando el archivo `config.ini`.

    * ¿DÓNDE ENCONTRARLO?
        * El archivo `config.ini` se crea automáticamente en el mismo directorio donde se encuentra el ejecutable del programa (o el script Python si lo ejecutas directamente).

    * ¿CÓMO EDITARLO?
        * Abre `config.ini` con cualquier editor de texto (Bloc de notas, Notepad++, VS Code, etc.).
        * Verás dos secciones principales: `[Colors]` y `[Settings]`.

    * SECCIÓN [Colors]:
        * Aquí encontrarás una lista de nombres de colores y sus valores (códigos hexadecimales como `#RRGGBB` o nombres de colores en inglés como "red", "blue", "white").
        * Ejemplo: `bg_dark = #2e2e2e`
        * `bg_dark`: Fondo principal de la ventana y los campos de número.
        * `bg_lighter`: Fondo de los recuadros de "Horas", "Minutos", "Segundos".
        * `button_color`: Color de fondo de los botones "Iniciar", "Cancelar", "Pausar", "Detener".
        * `button_active_color`: Color de fondo de los botones cuando pasas el ratón por encima (estado activo).
        * `spinbox_text_color`: Color de los números en los campos de Horas/Minutos/Segundos.
        * `clock_color_normal`: Color del texto del reloj cuando hay mucho tiempo restante.
        * `clock_color_orange`: Color del texto del reloj cuando el tiempo restante es menor a un umbral (por defecto, menos de 1 minuto).
        * `clock_color_red`: Color del texto del reloj cuando el tiempo restante es muy bajo (por defecto, menos de 30 segundos) y cuando la alarma está sonando.
        * `warning_message_color`: Color de fondo de la ventana emergente de aviso de apagado.
        * `cancel_button_color`: Color de fondo del botón "Cancelar Apagado".
        * `cancel_success_color`: Color de fondo de la ventana emergente de confirmación de cancelación.

    * SECCIÓN [Settings]:
        * `shutdown_warning_enabled`: Establece `True` para mostrar una advertencia y un botón de "Cancelar Apagado" cuando el temporizador llega a cero. Establece `False` para que el apagado sea directo sin aviso ni opción de cancelar desde la interfaz. Por defecto es `True`.

    * IMPORTANTE:
        * Después de realizar cambios en `config.ini`, **debes cerrar y volver a abrir el programa** para que los nuevos valores surtan efecto.
        * Asegúrate de que los valores de color sean válidos (códigos hexadecimales de 6 dígitos o nombres de colores web).
        * Asegúrate de que los valores de la sección `[Settings]` sean números enteros válidos (excepto `shutdown_warning_enabled` que debe ser `True` o `False`). Un valor inválido puede causar errores.

---

3.  TECLAS RÁPIDAS (ACCESOS DIRECTOS)

    Puedes controlar la ventana y el temporizador con las siguientes combinaciones de teclas:

    * CONTROL + FLECHA ARRIBA: Aumenta la transparencia de la ventana (se vuelve más opaca).
    * CONTROL + FLECHA ABAJO: Disminuye la transparencia de la ventana (se vuelve más transparente).
    * CONTROL + T: (Alternar) Muestra u oculta la barra de título de la ventana.
    * CONTROL + F: (Alternar) Activa o desactiva la función "Siempre en primer plano" (la ventana se mantendrá siempre visible sobre otras).

    * ARRASTRAR VENTANA:
        * Haz clic y arrastra con el **botón izquierdo del ratón** en cualquier parte de la ventana para moverla.

    * REDIMENSIONAR VENTANA:
        * Haz clic y arrastra con el **botón derecho del ratón** en una de las esquinas de la ventana para cambiar su tamaño.

---

¡Disfruta de tu temporizador de apagado automático!
""")
            except Exception as e:
                messagebox.showwarning("Error de Archivo", f"No se pudo crear instrucciones.txt: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("285x112")
    root.minsize(260, 95)
    root.attributes("-topmost", True)
    root.configure(bg="#2e2e2e")
    root.title("Apagado Automático")
    root.iconbitmap(ICON)
    timer = Timer(root)
    timer.pack(fill=tk.BOTH, expand=1)
    root.mainloop()
