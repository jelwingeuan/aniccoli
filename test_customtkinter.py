import customtkinter as ctk


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.title("CustomTkinter Test")
app.geometry("500x300")

label = ctk.CTkLabel(
    app,
    text="Animated Broccoli is working!",
    font=ctk.CTkFont(size=24, weight="bold"),
)
label.pack(padx=20, pady=(80, 20))

button = ctk.CTkButton(
    app,
    text="Test Button",
)
button.pack(padx=20, pady=10)

app.mainloop()