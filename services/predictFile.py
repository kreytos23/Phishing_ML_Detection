from services.utils import EmailParser, StringUtil
from joblib import load
import mailbox
import csv
import nltk
import pandas as pd
import os
import json
from collections import defaultdict
from flask import Flask, request, jsonify

class MboxProcessor:

  def __init__(self, archivo_mbox):
    self.archivo_mbox = archivo_mbox

  # Función para contar hojas puras
  def count_pure_leaves(modelo_rf, x_test):
    phishing_leaf_counts = []
    non_phishing_leaf_counts = []
    
    for x in x_test:
      phishing_count = 0
      non_phishing_count = 0
      
      for tree in modelo_rf.estimators_:
        leaf_index = tree.apply([x])[0]
        leaf_value = tree.tree_.value[leaf_index]
        if len(set(leaf_value[0])) == 1:  # Es una hoja pura
          if leaf_value[0][1] > 0:  # Clase phishing
            phishing_count += 1
          else:  # Clase no phishing
            non_phishing_count += 1
      
      phishing_leaf_counts.append(phishing_count)
      non_phishing_leaf_counts.append(non_phishing_count)
    
    return phishing_leaf_counts, non_phishing_leaf_counts
  

  def predict_mail(self):
    # Procesar el archivo .mbox
    malicious_words = []

    # Abrir el archivo CSV y leer los datos
    with open('utilsData/diccionarioPhishing.csv', 'r') as archivo:
      lector = csv.reader(archivo)
      next(lector)  # Omitir la cabecera si existe
      for fila in lector:
        # Convertir los elementos necesarios a enteros o el tipo de dato adecuado
        palabra, frecuencia = fila[0], int(fila[1])
        malicious_words.append((palabra, frecuencia))
    # Mostrar la lista de tuplas
    try:
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
        try:
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
        except Exception as e:
          numInvalidAddr += 1
      #else:
      #  numInvalidAddr += 1
      print("Numero de Correos con Direcciones Invalidas:", numInvalidAddr)
      df['noOfMaliciousWords'] = df['text'].apply(lambda x: len(
          set(x.keys()).intersection(set(dict(malicious_words).keys()))))
      df = df.drop(columns=['text'])
      
      modelo_rf = load('models/randomForestEmail_Spam350_ExtraPhishing_2.joblib')
      
      x_test = df.drop(columns=["class_label", "senderAddr", "receiverAddr"]).values
      y_pred = modelo_rf.predict(x_test)
      
      # Asume que df es tu DataFrame de entrenamiento original
      feature_names = df.drop(columns=["class_label", "senderAddr", "receiverAddr"]).columns.tolist()

      # Diccionario para almacenar los umbrales de cada característica
      thresholds = defaultdict(list)

      # Recorre cada árbol en el modelo
      for tree in modelo_rf.estimators_:
          tree_thresholds = tree.tree_.threshold
          tree_features = tree.tree_.feature
          for feature, threshold in zip(tree_features, tree_thresholds):
              if feature != -2:  # -2 indica que no es un nodo de división
                  feature_name = feature_names[feature]
                  thresholds[feature_name].append(threshold)

      # Convierte el diccionario a un DataFrame para análisis más sencillo
      thresholds_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in thresholds.items()]))

      # Imprime los umbrales promedio de cada característica
      average_thresholds = thresholds_df.mean()
      print(average_thresholds)      
      
      phishing_leaf_counts, non_phishing_leaf_counts = count_pure_leaves(modelo_rf, x_test)

      # Formar la respuesta JSON
      response = {
          "TotalEmails": len(y_pred),
          "Predictions": []
      }      
      
      for i, (email, pred) in enumerate(zip(df.to_dict(orient="records"), y_pred)):
          prediction = {
              "Sender Address": email["senderAddr"],
              "Results": int(pred),
              "All Features": {k: email[k] for k in feature_names}  # Todas las características con sus valores
              "Phishing Pure Leaves": phishing_count,
              "Non-Phishing Pure Leaves": non_phishing_count
          }  
          notable_features = {}
          for feature in feature_names:
              feature_value = email[feature]
              threshold = average_thresholds[feature]
              if pred == 1 and feature_value >= threshold:  # Phishing
                  notable_features[feature] = feature_value
              elif pred == 0 and feature_value < threshold:  # No Phishing
                  notable_features[feature] = feature_value
        
          
          sorted_notable_features = sorted(notable_features.items(), key=lambda x: abs(x[1] - average_thresholds[x[0]]), reverse=True)[:13]
          prediction["Notable Features"] = {k: v for k, v in sorted_notable_features}
          
          response["Predictions"].append(prediction)
    
      """
      address = df["senderAddr"].values
      noLinks = df["noOfUrls"].values
      noDotsUrls = df["noOfDotsInUrls"].values
      noSpecialChar = df["noOfSpecialCharsInUrls"].values
      noMaliciousWords = df["noOfMaliciousWords"].values

      dfAnswer = pd.DataFrame({'Sender Address': address, 'NoOfURL': noLinks, 
                               'NoDotsUrls': noDotsUrls, 'NoSpecialChar': noSpecialChar , 'noOfMaliciousWords': noMaliciousWords,
                               "Results": y_Prueba1})
      data_list = json.loads(dfAnswer.to_json(orient='records'))
      result = {
          "TotalEmails": len(data_list),
          "InvalidEmails": numInvalidAddr,
          "Predictions": data_list
      }
      final_json = json.dumps(result, indent=4)

    """
    
    except Exception as e:
      raise e
    os.remove(self.archivo_mbox)
    return response
