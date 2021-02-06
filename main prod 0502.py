# -*- coding: utf-8 -*-
import imaplib
import email
import requests
import json
from time import sleep

from email.header import decode_header
from bitrix24 import *
import telebot

print("Начинаем работу:")
globalsaver = 0
bot = telebot.TeleBot("")
bx24 = Bitrix24('url+token hear')
sdek_session = 0
session = requests.session()


def cdek_parser(inn):
    """
    :param inn:
    Получает инн компании которую надо найти.
    :return:
    Возвращает статус договора с этой компанией
    """
    try:

        print('Начинаем парсинг СДЭК')
        global sdek_session
        global session
        if sdek_session != 1:
            session = requests.session()
            r = session.get('https://contragent.cdek.ru/#/viewContragentPage')
            session.headers['Content-Type'] = 'application/json;charset=UTF-8'
            sleep(1)
            r = session.get('https://contragent.cdek.ru/')
            l_d = json.dumps({"login": "", "password": "", "lang": "rus"})
            sleep(1)
            login = session.post('https://contragent.cdek.ru/api/auth/login', data=l_d)



            session.headers['PWT'] = login.headers['PWT']
            session.headers['ETag'] = login.headers['ETag']
            sdek_session = 1

        inndata = json.dumps({"lang": "rus", "apiName": "contragent",
                              "apiPath": "/contragentEk5/getFilterData",
                              "limit": 50, "offset": 0, "timeOffset": -420,
                              "fields": [{"field": "innFullMatch", "value": inn}],
                              "columns": ["ek4Id", "country", "city", "name", "type", "inn",
                                          "subdivisionName", "kindOfActivity", "masterCity", "note"],
                              "sort": []})
        sleep(1)
        contragent = session.post('https://contragent.cdek.ru/api/preback', data=inndata)

        if contragent.status_code != 200:
            try:
                bot.send_message(496316511,
                                 'Парсер СДЭК. Ошибка: Авторизация/Аутентификация СДЭК не пройдена Login status' + str(contragent.status_code),
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
            except:
                pass
    except:
        bot.send_message(496316511,
                         'Парсер СДЭК. Ошибка: Авторизация/Аутентификация СДЭК не пройдена',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        print('Авторизация/Аутентификация СДЭК не пройдена')
        return 'Информация о договоре не найдена'
    # выдергиваем code
    try:
        code = json.loads(contragent.text)['items'][0]['code']
    except:
        return 'Информация о договоре не найдена'
    dogovor_req = json.dumps({"lang": "rus", "apiName": "contragent", "apiPath": "/contragentEk5/getOne",
                              "filter": {"code": code}})
    sleep(1)
    dogovor_status_raw = session.post('https://contragent.cdek.ru/api/preback', data=dogovor_req)

    result = json.loads(dogovor_status_raw.text)


    try:
        ret = str(
            result['contracts'][0]['contractTypeName'] + ', от ' + result['contracts'][0]['startDate'] + ' статус: ' +
            result['contracts'][0]['contractStatusName'])
    except:
        ret = 'Информация о договоре не найдена'
    return ret


def get_link_data(link):
    print('Запрос на страницу ATI...')

    try:
        id = link[(link.find('ID=') + 3):(link.find('&')):]
        r = requests.get('https://ati.su/api/passport/GetFirm/' + id)
        str_r = json.loads(r.text)
        inn = str_r['inn']
        return inn
    except KeyError:
        return None
    except:
        bot.send_message(496316511,
                         'Парсер СДЭК. Ошибка: Страница ATI не загружена. Проверьте сеть!',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        print('Ошибка: Страница ATI не загружена')
        return None


def lead_create(company_dict):
    # Ищем контакты по номеру телефона и добавляем компанию ID

    comp_exist = None
    prep_list_phone = []
    for i in company_dict:
        if i == 'contact1' or i == 'contact2':
            for e in company_dict[i]:
                if e == "phone1" or e == "phone2":
                    prep_list_phone.append(company_dict[i][e])

    try:
        find_comp = (bx24.callMethod('crm.duplicate.findbycomm', TYPE='PHONE', VALUES=prep_list_phone))
        comp_add_id = None
        pre_pre_id_c = None
        if len(find_comp) > 0:

            try:
                comp_add_id = find_comp['COMPANY'][::-1]
                # print('iz kompanii ' + comp_add_id)
                pre_pre_id_c = find_comp['CONTACT'][::-1][
                    0]  # если нашли в компании то добавляем и контакт если он есть
            except:
                try:
                    pre_pre_id_c = find_comp['CONTACT'][::-1][0]
                    try:
                        comp_add_id = bx24.callMethod('crm.contact.get', ID=pre_pre_id_c)['COMPANY_ID']
                    except BitrixError as message:
                        bot.send_message(496316511, 'Парсер СДЭК. Ошибка при добавлении компании в Б24 ' + str(message),
                                         reply_markup=telebot.types.ReplyKeyboardRemove())

                    # print('iz contacta ' + comp_add_id)
                except:
                    try:
                        pre_pre_id = find_comp['LEAD'][::-1]
                        comp_add_id = bx24.callMethod('crm.lead.get', ID=pre_pre_id)['COMPANY_ID']
                        # print('iz lead ' + comp_add_id)
                    except:
                        pass

        else:
            if comp_add_id == None:
                prep_list_mail = []
                for i in company_dict:
                    if i == 'contact1' or i == 'contact2':
                        prep_list_mail.append(company_dict[i]["email"])
                        # print('список мыл')

                try:
                    find_comp = (bx24.callMethod('crm.duplicate.findbycomm', TYPE='EMAIL', VALUES=prep_list_mail))
                    # print (find_comp)
                    if len(find_comp) > 0:
                        try:
                            comp_add_id = find_comp['COMPANY'][::-1][0]
                            # print('iz kompanii ' + comp_add_id)
                            try:
                                pre_pre_id_c = find_comp['CONTACT'][::-1][0]
                            except:
                                pass

                        except:
                            try:

                                pre_pre_id_c = find_comp['CONTACT'][::-1][0]
                                try:
                                    comp_add_id = bx24.callMethod('crm.contact.get', ID=pre_pre_id_c)['COMPANY_ID']
                                except BitrixError as message:
                                    bot.send_message(496316511,
                                                     'Парсер СДЭК. Ошибка при получении контакта в Б24 ' + str(message),
                                                     reply_markup=telebot.types.ReplyKeyboardRemove())

                                # print('iz contacta ' + comp_add_id)
                            except:
                                try:
                                    pre_pre_id = find_comp['LEAD'][::-1]
                                    comp_add_id = bx24.callMethod('crm.lead.get', ID=pre_pre_id)['COMPANY_ID']
                                    # print('iz lead ' + comp_add_id)
                                except:
                                    pass

                        if comp_add_id == None:
                            try:
                                comp_exist = 1
                                comp_add_id = bx24.callMethod('crm.company.add',
                                                              fields={'TITLE': company_dict["Company"],
                                                                      'WEB': {'n0': {"VALUE": company_dict["link"],
                                                                                     "VALUE_TYPE": "WORK"}}})
                            except BitrixError as message:
                                bot.send_message(496316511,
                                                 'Парсер СДЭК. Ошибка при добавлении компании в Б24 ' + str(message),
                                                 reply_markup=telebot.types.ReplyKeyboardRemove())





                except BitrixError as message:
                    bot.send_message(496316511,
                                     'Парсер СДЭК. Ошибка в самом начале поиска ID компании в Б24 ' + str(message),
                                     reply_markup=telebot.types.ReplyKeyboardRemove())
    except BitrixError as message:
        bot.send_message(496316511, 'Парсер СДЭК. Ошибка в самом начале поиска ID компании в Б24 ' + str(message),
                         reply_markup=telebot.types.ReplyKeyboardRemove())

    if comp_add_id == None:
        try:
            comp_exist = 1
            comp_add_id = bx24.callMethod('crm.company.add', fields={'TITLE': company_dict["Company"]})
        except BitrixError as message:
            bot.send_message(496316511, 'Парсер СДЭК. Ошибка при добавлении компании в Б24 ' + str(message),
                             reply_markup=telebot.types.ReplyKeyboardRemove())

    # Добавляем INN
    if comp_exist:
        try:
            rq_comp = (bx24.callMethod('crm.requisite.add', fields={"ENTITY_TYPE_ID": 4,
                                                                    'ENTITY_ID': comp_add_id,
                                                                    'PRESET_ID': 1,
                                                                    'NAME': 'Реквизиты',
                                                                    'RQ_INN': company_dict["inn"]}))
        except BitrixError as message:
            bot.send_message(496316511, 'Парсер СДЭК. Ошибка добавления Реквизитов в Б24 ' + str(message),
                             reply_markup=telebot.types.ReplyKeyboardRemove())

    # добавляем контакты
    if pre_pre_id_c == None:
        try:
            temp_dict = {"name": None, "phone1": None, "phone2": "", "email": None}
            temp_dict2 = {"name": None, "phone1": None, "phone2": "", "email": None}
            for i in company_dict["contact1"]:
                temp_dict[i] = company_dict["contact1"][i]

            for i in company_dict["contact2"]:
                temp_dict2[i] = company_dict["contact2"][i]
            pass
        except Exception:
            pass
        # print (comp_add_id)

        try:
            cont_add_id = (bx24.callMethod('crm.contact.add', fields={'COMPANY_IDS': {'VALUE': comp_add_id},
                                                                      'NAME': temp_dict["name"],
                                                                      'PHONE': {'n0': {"VALUE": temp_dict["phone1"],
                                                                                       "VALUE_TYPE": "MOBILE"},
                                                                                'n1': {"VALUE": temp_dict["phone2"],
                                                                                       "VALUE_TYPE": "WORK"}},
                                                                      'EMAIL': {'n0': {"VALUE": temp_dict["email"],
                                                                                       "VALUE_TYPE": "WORK"}}}))
        except BitrixError as message:
            bot.send_message(496316511, 'Парсер СДЭК. Ошибка добавления Контакта в Б24 ' + str(message),
                             reply_markup=telebot.types.ReplyKeyboardRemove())

        if temp_dict2["name"]:

            try:
                bx24.callMethod('crm.contact.add', fields={'COMPANY_IDS': {'VALUE': comp_add_id},
                                                           'NAME': temp_dict2["name"],
                                                           'PHONE': {'n0': {"VALUE": temp_dict2["phone1"],
                                                                            "VALUE_TYPE": "MOBILE"},
                                                                     'n1': {"VALUE": temp_dict2["phone2"],
                                                                            "VALUE_TYPE": "WORK"}},
                                                           'EMAIL': {'n0': {"VALUE": temp_dict2["email"],
                                                                            "VALUE_TYPE": "WORK"}}})
            except BitrixError as message:
                bot.send_message(496316511, 'Парсер СДЭК. Ошибка добавления Контакта2 в Б24 ' + str(message),
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        cont_add_id = pre_pre_id_c

    # print (comp_add_id)
    try:
        lead_id = bx24.callMethod('crm.lead.add', fields={'TITLE': company_dict["Company"],
                                                          'NAME': company_dict["Company"],
                                                          'PHONE': [{"VALUE": company_dict["contact1"]["phone1"],
                                                                     "VALUE_TYPE": "MOBILE"}],
                                                          'EMAIL': [{"VALUE": company_dict["contact1"]['email'],
                                                                     "VALUE_TYPE": "WORK"}],
                                                          'COMPANY_ID': comp_add_id,
                                                          'CONTACT_ID': cont_add_id,
                                                          'COMMENTS': company_dict['contract_status'],
                                                          'UF_CRM_1598602307825' : company_dict["inn"],
                                                          'UF_CRM_1603706403761' : 'Автоматически из письма'
                                                          })

    except BitrixError as message:
        bot.send_message(496316511, 'Парсер СДЭК. Ошибка добавления лида в Б24 ' + str(message),
                         reply_markup=telebot.types.ReplyKeyboardRemove())
    print('Создан лид: ' + str(lead_id))
    return "OK"


def check_data(company_dict, innset):
    try:
        if company_dict['contract_status'].split(' ')[-1] != "Подписан" and str(
                company_dict["inn"]) not in innset and str(company_dict["inn"]) != 'None':
            addinntofile(company_dict["inn"])
            return True
        if company_dict['Договор'].split(' ')[-1] == "Подписан":
            addinntofile(company_dict["inn"])    

        return False
    except KeyError:

        return False


def loadinnfile():
    innset = []
    try:
        with open("innlist.txt", 'r') as innfile:
            [innset.append(inn.strip().split()[0]) for inn in innfile]
        return innset
    except:
        bot.send_message(496316511, 'Парсер СДЭК.' + 'Ошибка: не могу прочитать файл со списком ИНН ')


def addinntofile(inn):
    global innset
    innset.append(inn)
    try:
        with open("innlist.txt", 'a') as file:
            file.write('\n' + str(inn))

    except:
        bot.send_message(496316511, 'Парсер СДЭК.' + 'Ошибка: не могу записать файл со списком ИНН ')


if __name__ == "__main__":
    company_dict = {}
    sdek_session = 0
    innset = []

    try:
        mail = imaplib.IMAP4_SSL('imap.mail.ru')
        mail.login('', '')
        mail.list()
        mail.select("INBOX")

    except:
        print('Не могу подключиться к серверу. Проверьте сеть! ')
        bot.send_message(496316511, 'Парсер СДЭК.' + 'Ошибка Не могу подключиться к серверу. Проверьте сеть',
                         reply_markup=telebot.types.ReplyKeyboardRemove())
    try:
        result, data = mail.search(None, "UNSEEN")

        print('Получение почты: ' + result)
        innset = loadinnfile()
        ids = data[0]
        id_list = ids.split()

        for i in id_list:

            result, data = mail.fetch(i, "(RFC822)")
            test = data
            raw_email = data[0][1]
            try:
                raw_email_string = raw_email.decode('utf-8')
            except:
                print('Ошибка декодирования заголовка')
                bot.send_message(496316511, 'Парсер СДЭК. Ошибка декодирования заголовка ',
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
                pass

            email_message = email.message_from_string(raw_email_string)
            sub = email_message.get('subject')
            try:
                bytes, encoding = decode_header(sub)[0]
            except:
                bot.send_message(496316511, 'Парсер СДЭК. Ошибка декодирования заголовка ',
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
                print('Ошибка декодирования заголовка')
                pass
            if bytes.decode(encoding).find("Добавлен груз") >= 0:

                if email_message.is_multipart():
                    for payload in email_message.get_payload():
                        body = payload.get_payload(decode=True).decode('utf-8')
                else:
                    body = email_message.get_payload(decode=True).decode('utf-8')
                mail_b = body
                company_name_raw = mail_b[mail_b.find('ФИРМА:'):mail_b.find('</a>')]
                company_dict['Company'] = company_name_raw[company_name_raw.rfind('>') + 1:]
                company_link_raw = company_name_raw[company_name_raw.find('"') + 1:]
                company_dict['link'] = company_link_raw[:company_link_raw.find('"')]

                # получаем данные по ссылке ATI
                company_dict['inn'] = get_link_data(company_dict['link'])

                # формируем блоки для поиска
                findblock = mail_b[mail_b.find('ФИРМА:'): mail_b.find('По фильтру:')]
                name1_raw = findblock[findblock.find('<br><br>') + 8:findblock.find('АТИ')]
                name2_raw = findblock[findblock.rfind('<br><br>') + 8:findblock.rfind('АТИ')]
                mail1_raw = name1_raw[
                            name1_raw.find('Mail:'): name1_raw.find('Mail:') + name1_raw[
                                                                               name1_raw.find('Mail:'):].find(
                                '</a>')]
                mail2_raw = name2_raw[
                            name2_raw.find('Mail:'): name2_raw.find('Mail:') + name2_raw[
                                                                               name2_raw.find('Mail:'):].find(
                                '</a>')]

                # Выцарапываем номера телефонов (надеюсь это никто не увидит, но регулярки (пока) выше моего понимания)

                phone1 = name1_raw[name1_raw.find("Ref'>") + 5:name1_raw[name1_raw.find("Ref'>") + 5:].find(
                    '<') + name1_raw.find("Ref'>") + 5:]

                last_c = name1_raw[name1_raw.find("Ref'>") + 5:].find('<') + name1_raw.find("Ref'>") + 5

                shortdata = name1_raw[last_c:]
                mail1 = mail1_raw[mail1_raw.rfind('>') + 1:]

                if shortdata.find('+') != -1:
                    phone2 = shortdata[
                             shortdata.find("Ref'>") + 5:shortdata[shortdata.find("Ref'>") + 5:].find(
                                 '<') + shortdata.find("Ref'>") + 5:]

                    company_dict['contact1'] = {'name': name1_raw[:name1_raw.find('<')],
                                                'phone1': phone1,
                                                'phone2': phone2,
                                                'email': mail1}
                else:
                    company_dict['contact1'] = {'name': name1_raw[:name1_raw.find('<')],
                                                'phone1': phone1,
                                                'email': mail1}

                # Обрабатываем второго:
                if name2_raw != name1_raw:
                    phone11 = name2_raw[
                              name2_raw.find("Ref'>") + 5:name2_raw[name2_raw.find("Ref'>") + 5:].find(
                                  '<') + name2_raw.find("Ref'>") + 5:]

                    last_c2 = name2_raw[name1_raw.find("Ref'>") + 5:].find('<') + name2_raw.find("Ref'>") + 5
                    shortdata2 = name2_raw[last_c2:]
                    mail2 = mail2_raw[mail2_raw.rfind('>') + 1:]

                    if shortdata2.find('+') != -1:

                        phone22 = shortdata2[
                                  shortdata2.find('+'):shortdata2[shortdata2.find("Ref'>") + 5:].find(
                                      "Ref'>") + 5 + shortdata2.find("Ref'>") + 5:]

                        company_dict['contact2'] = {'name': name2_raw[:name2_raw.find('<')],
                                                    'phone1': phone11,
                                                    'phone2': phone22,
                                                    'email': mail2}
                    else:
                        company_dict['contact2'] = {'name': name2_raw[:name2_raw.find('<')],
                                                    'phone1': phone1,
                                                    'email': mail2}

                # Начинаем поиск состояния договора по ИНН
                if company_dict['inn'] not in innset:
                    if company_dict['inn']:
                        dogovor_status = cdek_parser(company_dict['inn'])
                        print('Парсинг СДЭК - ОК')
                        company_dict['contract_status'] = dogovor_status  # Вот тут полностью сформировали словарь

                    if check_data(company_dict, innset):
                        lead_create(company_dict)

                company_dict = {}  # Обнуляем некоторые переменные


            else:
                print('Тема письма без "Добавлен груз"')
    except IndexError as e:
        print("Новых писем не найденно" + str(e))
    print('Все сделали')
    innset = []
    sdek_session = 0



    # mail = read_file('mail2.txt')

    # вырезаем имя и ссылку
    # Добавляем компанию в словарь и ссылку на нее
