import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1280x720")
        self.title("OTEC Downloader")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame = ctk.CTkScrollableFrame(master=self)
        self.frame.grid(row=0, column=0, sticky="nsew")

        # Botón de opción
        radiobutton_frame = ctk.CTkFrame(self.frame)
        radiobutton_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        radiobutton_label = ctk.CTkLabel(radiobutton_frame, text="Selecciona una opción:")
        radiobutton_label.grid(row=0, column=0, padx=10, pady=10)
        self.radiobutton_var = ctk.StringVar(value="Opción 1")
        radiobutton1 = ctk.CTkRadioButton(radiobutton_frame, text="Opción 1", variable=self.radiobutton_var, value="Opción 1")
        radiobutton1.grid(row=0, column=1, padx=10, pady=10)
        radiobutton2 = ctk.CTkRadioButton(radiobutton_frame, text="Opción 2", variable=self.radiobutton_var, value="Opción 2")
        radiobutton2.grid(row=0, column=2, padx=10, pady=10)

        self.id_var = ctk.IntVar(value="1")
        entry = ctk.CTkEntry(radiobutton_frame, width=200, textvariable=self.id_var).grid(row=1, column=0, columnspan=3)

        # Boton de añadir

        # Botón de descarga
        button = ctk.CTkButton(self.frame, text="Descargar", command=self.mostrar_mensaje)
        button.grid(row=0, column=1)

    def mostrar_mensaje(self):
        print(self.radiobutton_var.get())
        print(self.id_var.get())

if __name__ == "__main__":
    app = App()
    app.mainloop()