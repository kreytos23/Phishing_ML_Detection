from flask import Flask, request, Response
from services.predictFile import MboxProcessor
from flask_cors import cross_origin
import os

app = Flask(__name__)

#Hello World en la raíz de la aplicación
@app.route('/')
@cross_origin(origins="*")
def hola_mundo():
  return 'Hola Mundo!'


@app.route('/upload-mbox', methods=['POST'])
@cross_origin(origins="*")
def upload_mbox():
  # Verificar si la petición tiene el archivo parte
  if 'mbox_file' not in request.files:
    return "No mbox_file part in request", 400

  file = request.files['mbox_file']

  # Si el usuario no selecciona un archivo, el navegador
  # también puede enviar una parte vacía sin nombre de archivo
  if file.filename == '':
    response = Response(response="No file in request",
                        status=400)
    return response

  if file and file.filename.endswith('.mbox'):
    # Guardar el archivo temporalmente en disco
    temp_path = os.path.join('temp', file.filename)
    file.save(temp_path)
    try:
      mboxProcessor = MboxProcessor(temp_path)
      results = mboxProcessor.predict_mail()
    except Exception as e:
      response = Response(response=str(e),
                          status=500)
      return response
    response = Response(response=results,
                        status=200,
                        mimetype='application/json')
    return response
  else:
    response = Response(response="Unsupported file type",
                        status=400)
    return response  



if __name__ == '__main__':
  app.run(debug=True)
