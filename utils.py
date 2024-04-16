import re
import os
import nltk
import string
import mailbox
import pandas as pd
from bs4 import BeautifulSoup
from collections import Counter
from nltk.corpus import stopwords
from email.header import decode_header
from nltk.tokenize import word_tokenize
from joblib import dump

# Clase EmailParser se utiliza para extraer las características de los correos que se pasen por parámetros, características como URLs, No. de Datos adjuntos
# contenido HTML y contenido en texto plano
class EmailParser:
    urlRegex = r'https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=;]*)'
    emailRegex = r'([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)'

# Constructor del método main
    def __init__(self, email):
        self.email = email
        self.__extract_email_parts()

#This method iterates over the parts of the email message using the walk() method.
#It checks the content type of each part and based on that,
#extracts the text, HTML content, and counts the number of attachments. 

    def __extract_email_parts(self):
        no_of_attachments = 0
        text = str(self.email['Subject']) + " "
        htmlDoc = ""
        for part in self.email.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                text += str(part.get_payload())
            elif content_type == 'text/html':
                htmlDoc += part.get_payload()
            else:
                main_content_type = part.get_content_maintype()
                if main_content_type in ['image','application']:
                    no_of_attachments += 1
        self.text, self.html, self.no_of_attachments = text, htmlDoc, no_of_attachments

 #This method returns a list of URLs found in both the text and HTML content of the email.
 #It uses regular expressions and the urlRegex class variable to match and extract URLs from the text and HTML.

    def get_urls(self):
        text_urls = set(re.findall(EmailParser.urlRegex,self.text))
        html_urls = set(re.findall(EmailParser.urlRegex,self.html))
        return list(text_urls.union(html_urls))

    #This method returns the text content of the email. If HTML content is present
    def get_email_text(self):
        if(self.html != ""):
            soup = BeautifulSoup(self.html, 'lxml')
            self.text += soup.text
        return self.text

    #This method returns the number of attachments found in the email
    def get_no_of_attachments(self):
        return self.no_of_attachments

    #This method returns the email address of the sender.
    #It retrieves the sender's information from the email parameter passed to the constructor.
    def get_sender_email_address(self):
        sender = self.email['From']
        try:
            emails = re.findall(EmailParser.emailRegex, sender)
        except:
            h = decode_header(self.email['From'])
            header_bytes = h[0][0]
            sender = header_bytes.decode('ISO-8859-1')
            emails = re.findall(EmailParser.emailRegex, sender)
        if(len(emails) != 0):
            return emails[len(emails)-1]
        else:
            return ''

    #This method returns the email address of the receiver.
    #It retrieves the receiver's information from the email parameter passed to the constructor.
    def get_receiver_email_address(self):
        receiver = self.email['To']
        try:
            emails = re.findall(EmailParser.emailRegex, receiver)
        except:
            h = decode_header(self.email['To'])
            header_bytes = h[0][0]
            receiver = header_bytes.decode('ISO-8859-1')
            emails = re.findall(EmailParser.emailRegex, receiver)
        if(len(emails) != 0):
            return emails[len(emails)-1]
        else:
            return ''



#provide various utility methods for processing text, URLs, and email addresses
class StringUtil:

    dotRegex = r'\.'
    digitsRegex = r'[0-9]'
    ipAddressRegex = r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
    dashesRegex = r'-'
    specialCharsRegex = r'[()@:%_\+~#?\=;]'
    words = Counter()
    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))
    stemmer = nltk.PorterStemmer()
    punctuations = ['!','@','#','$','%','^','&','*','(',')','-','_','=','+',';',':',"'",'"','?','/','<','>','.',',','/','~','`']


    #This method takes a list of URLs as input and processes them.
    #It counts the number of dots, dashes, and special characters in each URL
    def process_urls(self,urls):
        noOfDots, noOfDashes, noOfSpecialChars, hasIpAddressInUrl, noOfIpAddress, noOfHttpsLinks = 0,0,0,0,0,0
        for url in urls:
            if url.startswith('https://'):
                noOfHttpsLinks += 1
            noOfDots += len(re.findall(StringUtil.dotRegex,url))
            noOfDashes += len(re.findall(StringUtil.dashesRegex,url))
            noOfSpecialChars += len(re.findall(StringUtil.specialCharsRegex,url))
            noOfIpAddress += len(re.findall(StringUtil.ipAddressRegex, url))
        if noOfIpAddress > 0:
            hasIpAddressInUrl = 1
        return len(urls), noOfDots, noOfDashes, noOfSpecialChars, hasIpAddressInUrl, noOfIpAddress, noOfHttpsLinks


    #This method takes a string of text as input and processes it. It performs several operations on the text, including converting it to lowercase,
    #removing escape sequences, removing punctuation and digits, tokenizing the text into individual words
    def process_text(self, text):
        text = text.lower()                    #lowercase
        text = re.sub(r'[\n\t\r]', ' ', text)  #remove escape sequences

        #remove punctuations
        punctuation = string.punctuation  # Get all punctuation marks
        translator = str.maketrans('', '', punctuation + string.digits)  # Create a translator to remove punctuation and digits
        text = text.translate(translator)  # Remove punctuation and digits using translate()

        #tokenize and stem words
        word_tokens = word_tokenize(text)
        filtered_text = []
        for w in word_tokens:
            if w not in StringUtil.stop_words:
                filtered_text.append(w)

        #count frequency of words
        word_counts = Counter(filtered_text)
        stemmed_word_count = Counter()
        for word, count in word_counts.items():
            stemmed_word = StringUtil.stemmer.stem(word)
            stemmed_word_count[stemmed_word] += count
        word_counts = stemmed_word_count
        StringUtil.words += word_counts
        return word_counts

    #This method takes an email address as input and processes it. It calculates various metrics related to the email address,
    #including its length, the counts of dots, dashes, special characters, digits, and subdomains
    def process_email_address(self, emailid):
        length, noOfDots, noOfDashes, noOfSpecialChars, noOfDigits, noOfSubdomains = 0,0,0,0,0,0

        length = len(emailid)
        if(length > 0):
            username, domain = emailid.split('@')
            noOfSubdomains = len(re.findall(StringUtil.dotRegex,domain)) - 1
            noOfDots = len(re.findall(StringUtil.dotRegex, username))
            noOfSpecialChars = len(re.findall(StringUtil.specialCharsRegex, username))
            noOfDashes = len(re.findall(StringUtil.dashesRegex, emailid))
            noOfDigits = len(re.findall(StringUtil.digitsRegex, emailid))

        return length, noOfDots, noOfDashes, noOfSpecialChars, noOfDigits, noOfSubdomains

        #This method returns the 1000 most common words encountered so far in the text processing.
        #It accesses the class variable StringUtil.words,
        #which is a Counter object that keeps track of word frequencies across all processed texts.
    def get_most_common_words(self):
        return StringUtil.words.most_common(1000)