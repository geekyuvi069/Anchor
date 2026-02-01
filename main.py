import typer

app = typer.Typer()

@app.command()
def main():
    print("AI-Edit CLI Tool")

if __name__ == "__main__":
    app()
