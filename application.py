from flask import Flask, request
from services.predictFile import MboxProcessor
import os

app = Flask(__name__)


@app.route('/')
def hola_mundo():
  return 'Hola Mundo!'

'''
@app.route('/upload-mbox', methods=['POST'])
def upload_mbox():
  # Verificar si la petición tiene el archivo parte
  if 'mbox_file' not in request.files:
    return "No mbox_file part in request", 400

  file = request.files['mbox_file']

  # Si el usuario no selecciona un archivo, el navegador
  # también puede enviar una parte vacía sin nombre de archivo
  if file.filename == '':
    return "No selected file", 400

  if file and file.filename.endswith('.mbox'):
    # Guardar el archivo temporalmente en disco
    temp_path = os.path.join('temp', file.filename)
    file.save(temp_path)
    mboxProcessor = MboxProcessor(temp_path)
    results = mboxProcessor.predict_mail()
    return results, 200
  else:
    return "Unsupported file type", 400
'''

if __name__ == '__main__':
  app.run(debug=True)
