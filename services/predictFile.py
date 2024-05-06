from services.utils import EmailParser, StringUtil
from joblib import load
import mailbox
import csv
import nltk
import pandas as pd
import os


class MboxProcessor:

  def __init__(self, archivo_mbox):
    self.archivo_mbox = archivo_mbox

  def predict_mail(self):
    # Procesar el archivo .mbox
    malicious_words = []

    # Abrir el archivo CSV y leer los datos
    with open('utilsData/datos.csv', 'r') as archivo:
      lector = csv.reader(archivo)
      next(lector)  # Omitir la cabecera si existe
      for fila in lector:
        # Convertir los elementos necesarios a enteros o el tipo de dato adecuado
        palabra, frecuencia = fila[0], int(fila[1])
        malicious_words.append((palabra, frecuencia))
    # Mostrar la lista de tuplas
    test_emails = mailbox.mbox(self.archivo_mbox)
    dominios_permitidos = [".ipn", ".edu", ".unam"]
    nltk.download('punkt')
    df = pd.DataFrame(columns=[
        'text', 'lengthOfEmailId', 'noOfDotsInEmailId', 'noOfDashesInEmailId',
        'noOfSpecialCharsInEmailId', 'noOfDigitsInEmailId',
        'noOfSubdomainsInEmailId', 'noOfUrls', 'noOfDotsInUrls',
        'noOfDashesInUrls', 'noOfSpecialCharsInUrls', 'hasIpAddressInUrls',
        'noOfIpAddressInUrls', 'noOfHttpsLinks', 'no_of_attachments',
        'senderAddr', 'class_label', 'receiverAddr'
    ])
    stringUtil = StringUtil()
    numInvalidAddr = 0
    for email in test_emails:
      emailParser = EmailParser(email)
      receiverAddr = emailParser.get_receiver_email_address()
      #if any(dominio in receiverAddr for dominio in dominios_permitidos):
      no_of_attachments = emailParser.get_no_of_attachments()
      emailid_features = stringUtil.process_email_address(
          emailParser.get_sender_email_address())
      urls_features = stringUtil.process_urls(emailParser.get_urls())
      word_dict = stringUtil.process_text(emailParser.get_email_text())
      senderAddr = emailParser.get_sender_email_address()
      df.loc[len(df)] = [
          word_dict, emailid_features[0], emailid_features[1],
          emailid_features[2], emailid_features[3], emailid_features[4],
          emailid_features[5], urls_features[0], urls_features[1],
          urls_features[2], urls_features[3], urls_features[4],
          urls_features[5], urls_features[6], no_of_attachments, senderAddr, 0,
          receiverAddr
      ]
      #else:
      #  numInvalidAddr += 1
    print("Numero de Correos con Direcciones Invalidas:", numInvalidAddr)
    df['noOfMaliciousWords'] = df['text'].apply(lambda x: len(
        set(x.keys()).intersection(set(dict(malicious_words).keys()))))
    df = df.drop(columns=['text'])
    xTest = df.drop(
        columns=["class_label", "senderAddr", "receiverAddr"]).values
    yTest = df["class_label"].values

    modelo_rf = load('models/randomForestEmail.joblib')
    y_Prueba1 = modelo_rf.predict(xTest)
    address = df["senderAddr"].values
    dfAnswer = pd.DataFrame({'Sender Address': address, "Results": y_Prueba1})
    json_resultado = dfAnswer.to_json(orient='index')
    print(json_resultado)

    os.remove(self.archivo_mbox)
    return json_resultado