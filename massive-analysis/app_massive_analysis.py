import streamlit as st
import pandas as pd
import io
import requests
import xlsxwriter
import openpyxl

# API data
api_url = "https://api.buydepa.dev/"
api_key = 'ZsmyCP63oR4W5ZFGC780V5t7naQOb2bh6bUfIBID'
my_headers = {'x-api-key': api_key, 'client-id': 'buydepa',
              'Content-Type': 'application/json'}


def coordinates_management(num):
    return float(f"{str(num)[0:3]}.{str(num)[3:]}")


def internal_pricing_analysis_request(inputvar):
    return requests.post(f"{api_url}v1/internal-pricing-analysis", json=inputvar, headers=my_headers)


def read_excel(start_index, end_index, file):
    data = pd.read_excel(file)
    data = data.head(end_index)
    data = data.tail(end_index - start_index)
    offers = []
    messages = []
    quotation_codes = []
    last_index = -1
    inferior_offers_limits = []
    superior_offers_limits = []
    for i in data.index:
        if i > last_index:
            inputvar = {'currency': 'UF', 'antiquity': 0}
            try:
                inputvar['ask_price'] = int(data['precioReferenciaUF'][i])
                inputvar['address'] = f"{data['ITE_ADD_STREET'][i]},{data['ITE_ADD_CITY_NAME'][i]}"
                inputvar["commune"] = data['ITE_ADD_CITY_NAME'][i].upper()
                inputvar['bathrooms'] = (
                    data['banos'][i] != None and int(data['banos'][i])) or -1
                inputvar['bedrooms'] = int(data['dormitorios'][i])
                inputvar['area_total'] = float(data['sup_total'][i])
                inputvar['area_ext'] = float(
                    data['sup_total'][i] - data['sup_const'][i])
                inputvar['item_id'] = str(data['ITE_ITEM_ID'][i])
                inputvar['garages'] = int(data['estacionamientos'][i])
                if 'lat' in data and 'lon' in data:
                    inputvar['lat'] = coordinates_management(data['lat'][i])
                    inputvar['lng'] = coordinates_management(data['lon'][i])
            except:
                pass
            try:
                response = internal_pricing_analysis_request(inputvar).json()
            except:
                response = {}
            if 'offer' in response and 'message' in response and 'errors' not in response:
                messages.append(response['message'])
                offers.append(response['offer'])
                quotation_codes.append(response['quotation_code'])
                if 'inferior_offer_limit' in response and 'superior_offer_limit' in response:
                    inferior_offers_limits.append(
                        response['inferior_offer_limit'])
                    superior_offers_limits.append(
                        response['superior_offer_limit'])
                else:
                    inferior_offers_limits.append(
                        0)
                    superior_offers_limits.append(
                        0)
                print(
                    f"{i}: Offer: {response['offer']}. Message: {response['message']}")
            elif 'errors' in response:
                messages.append(response['errors'])
                offers.append(False)
                inferior_offers_limits.append(0)
                superior_offers_limits.append(0)
            else:
                messages.append('Error no identificado')
                offers.append(False)
                inferior_offers_limits.append(0)
                superior_offers_limits.append(0)
    data.insert(0, "Message", messages, True)
    data.insert(0, "Quotation code", quotation_codes, True)
    data.insert(0, "Límite superior", superior_offers_limits, True)
    data.insert(0, "Límite inferior", inferior_offers_limits, True)
    data.insert(0, "Offer", offers, True)
    true_offers = data.loc[data['Offer'] == True]
    dealers = true_offers.loc[true_offers['User_Type'] == 'Dealer']
    non_dealers = true_offers.loc[true_offers['User_Type'] != 'Dealer']
    return data, dealers, non_dealers


def main(file, start_index, end_index):
    return read_excel(start_index, end_index, file)


def index_options_generator(length):
    max_option = length - (length % 1000) + 1000
    return [index for index in range(1000, max_option + 1, 1000)]


def app():

    st.set_page_config(page_title="Massive analysis")

    st.title("Massive analysis")

    uploaded_file = st.file_uploader(
        "",
        key="1",
        help="Here you have to upload your excel for analysis"
    )

    if uploaded_file is not None:
        file_container = st.expander("Check your uploaded .xlsx")
        shows = pd.read_excel(uploaded_file)
        uploaded_file.seek(0)
        file_container.write(shows)
        input_options = index_options_generator(len(shows))
        start_index = st.selectbox(
            'Start index', input_options, index=0, disabled=False)
        end_index = st.selectbox(
            'End index', input_options, index=0, disabled=False)

        if st.button('Analize', disabled=uploaded_file == None and start_index == end_index):
            buffer = io.BytesIO()
            with st.spinner(text=f'Analizing from {start_index} to {end_index} ...'):
                data, dealers, non_dealers = main(
                    uploaded_file, start_index, end_index)
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    data.to_excel(writer, sheet_name='BUYDEPA DATA')
                    dealers.to_excel(writer, sheet_name='DEALERS')
                    non_dealers.to_excel(writer, sheet_name='NON DEALERS')
                    writer.save()
                    st.download_button(
                        label=f"Download {start_index} to {end_index}",
                        data=buffer,
                        file_name=f"{start_index}-{end_index}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
            st.success('Done!')


# Start app
app()
