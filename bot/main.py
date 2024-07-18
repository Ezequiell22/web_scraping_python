from playwright.sync_api import sync_playwright, Page
from query import execute_select, execute_sql
from comuns import abreviatura_a_estado, desc_info_complementares
import os
from dotenv import load_dotenv
import logging
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=os.environ['TOKEN_SLACK'])

load_dotenv()


logging.basicConfig(filename='app_log.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def SendMessageSlack(msg):
    channel_id = os.environ['CHANNEL_ID_SLACK']

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=msg
        )
        print(f"Mensagem enviada: {response['message']['text']}")

    except SlackApiError as e:
        print(f"Erro ao enviar mensagem: {e.response['error']}")


def tela_mercadorias(page: Page, ncm, cest):
    logging.info('tela_mercadorias')
    page.goto(os.environ['URL_BUSCA_NCM'])

    page.wait_for_timeout(5000)
    input_ncm_parcial = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[1]/div/input')
    input_ncm_parcial.fill(ncm[:4])

    btn_buscar = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[1]/button')
    btn_buscar.click()

    page.wait_for_timeout(7000)
    div_selector = '.ronaldo .body-resultado'
    div_elements = page.query_selector_all(div_selector)

    for div_item_handle in div_elements:
        div_item = div_item_handle.as_element()
        # Seleciona todas as divs filhas de .nfe
        nfe_elements = div_item.query_selector_all('.nfe > div')
        dest_element = div_item.query_selector('.dest')

        for nfe_element in nfe_elements:

            nfe_content = nfe_element.inner_text()
            dest_content = dest_element.inner_text()

            nfe_content = nfe_content.replace('.', '')
            dest_content = dest_content.replace('.', '')

            if ((ncm in nfe_content) or (nfe_content in ncm)) and (cest != '') and (cest in str(dest_content).strip()):

                logging.info('------')
                logging.info(dest_content)
                logging.info(cest)
                button_element = div_item.query_selector('.selecionar')
                if button_element:
                    button_element.click()
                    return True
                    break

    else:
        logging.info('NCM não encontrado')
        return False


def telaDadosDoItem(page: Page, vlr_unit, vlr_ipi, qtd, vlr_frete, perc_fcp, aliq_interna_dest, perc_redu, perc_desc, origem):

    logging.info([vlr_unit, vlr_ipi, qtd, vlr_frete,
                 perc_fcp, aliq_interna_dest, perc_redu, perc_desc])

    logging.info('telaDadosDoItem')
    page.wait_for_timeout(5000)

    valor_da_mercadoria_unit = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[2]/input')
    valor_da_mercadoria_unit.fill(vlr_unit)

    valor_ipi = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[3]/div/input')
    valor_ipi.fill(vlr_ipi)

    quantidade = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[4]/input')
    quantidade.fill(qtd)

    frete = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[6]/input')
    frete.fill(vlr_frete)

    perc_fund_combat = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[7]/input')
    perc_fund_combat.fill(perc_fcp)

    logging.info(float(perc_redu))

    if (float(perc_redu) < 100):
        perc_redu_locator = page.locator(
            '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[10]/div/input')
        perc_redu_locator.fill(perc_redu)

    perc_desc_locator = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[8]/input')
    perc_desc_locator.fill(perc_desc)

    aliq_interna_dest_locator = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[9]/div/input')
    aliq_interna_dest_locator.fill(aliq_interna_dest)

    if (origem == 'IMP'):
        check_iternacional = page.locator(
            '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[13]/label/span')
        check_iternacional.click()

    page.wait_for_timeout(1000)
    bt_incluir = page.locator(
        '//*[@id="__layout"]/div/main/section/div/div[6]/div/div[14]/button')
    bt_incluir.click()
    page.wait_for_timeout(1000)


def getStrSql():

    return f"""
        select 
        uf_emit, nr_ncm, nr_cest, vlr_ipi, vlr_it, 
        cast(qt_it as int ) qt_it, vlr_frete_it, aliq_int,
        nr_nf, perc_fcp, cd_nf, crt, cd_prod, PERC_REDU_BASE_ICMS,
        perc_desc, org, cd_filial, SEQ_ITEM
        from 
        v_itens_lefisc
        where dt_ent  >= '2023-08-01'
        and aliq_int > 0
        order by cd_nf
    """


def logVerificados(cd_nf, cd_prod, cd_filial, seq_item, qtd):
    insert_query = f"""
            insert into log_verificados_lefisc ( cd_prod, cd_nf, cd_filial, num_item, quantidade )
            values ( ?, ? , ? , ?, ?)
            """

    execute_sql(insert_query, [cd_prod, cd_nf, cd_filial, seq_item, qtd])
    logging.info("Inserindo log de notas verificada " +
                 str(cd_nf) + " cd_prod " + str(cd_prod))


def getTasks(page: Page):

    queryStr = getStrSql()
    results = execute_select(queryStr)
    logging.info(len(results))

    SendMessageSlack('Total Tasks ' + str(len(results)))

    for index, row in enumerate(results):
        logging.info(row)
        logging.info(str(index) + ' of ' + str(len(results)))

        estado_origem = abreviatura_a_estado(row[0])
        estado_destino = 'Rio Grande do Sul'
        text_complementar = desc_info_complementares(row[11])
        text_tp_operacao = "MVA Regularização - Mercadoria oriunda de outra UF"
        vlr_unit = f"{row[4]:,.2f}"
        vlr_ipi = f"{row[3]:,.2f}"
        qtd = str(row[5])
        vlr_frete = str(row[6])
        perc_fcp = row[9]
        aliq_interna_dest = str(row[7])
        ncm = str(row[1])
        cest = str(row[2])
        cd_nf = str(row[10])
        cd_prod = str(row[12])
        perc_redu = f"{row[13]:,.2f}"
        perc_desc = f"{row[14]:,.2f}"
        origem = str(row[15])
        cd_filial = row[16]
        seq = str(row[17])

        processarCabecalho(page, ncm, estado_origem,
                           estado_destino, text_complementar, text_tp_operacao)

        # itens
        processarItem(page, ncm, cest, vlr_unit, vlr_ipi,
                      qtd, vlr_frete, perc_fcp, aliq_interna_dest, perc_redu, perc_desc, origem)

        finalizar_calculo(page, cd_nf, cd_prod, cd_filial, seq)

        # insere no log verificados
        logVerificados(cd_nf, cd_prod, cd_filial, seq, qtd)

    SendMessageSlack('End Tasks')


def finalizar_calculo(page: Page, cd_nf, cd_prod, cd_filial, num_item):
    logging.info('finalizar_calculo')
    page.wait_for_timeout(1000)
    bt_finalizar = page.get_by_text(" Finalizar Cálculo")
    bt_finalizar.click()
    telaRelatorioFinal(page, cd_nf, cd_prod, cd_filial, num_item)


def deleta_se_existe(array: list):
    logging.info('deleta_se_existe')
    logging.info(array[14])
    logging.info(array[15])
    logging.info(array[1])

    strSqlDel = f"""
    delete from log_fiscal_lefisc
    where cd_prod = {array[14]}
    and cd_nf = {array[15]}
    and quantidade = '{array[1]}'
    """

    execute_sql(strSqlDel)


def insertDataTable(array: list):
    deleta_se_existe(array[0])

    logging.info('insertDataTable')
    logging.info(array)
    insert_query = (
        "INSERT INTO log_fiscal_lefisc "
        "(CEST, QUANTIDADE, VLR_UNITARIO, ALIQ_INTERNA, MVA, IPI, DESPESAS, FRETE, BASE_ICMS_PROPRIO, ICMS_PROPRIO, BASE_ST, ST, vl_desc, NCM , CD_PROD, CD_NF, CREATED_AT, CD_FILIAL, NUM_ITEM ) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,  GETDATE(), ? , ? )")

    execute_sql(insert_query, array)


def telaRelatorioFinal(page: Page, cd_nf, cd_prod, cd_filial, num_item):
    page.wait_for_timeout(3000)

    current_url = page.url
    url = os.environ.get('URL_RESULTADO')

    logging.info(current_url)
    logging.info(url)

    if current_url != os.environ.get('URL_RESULTADO'):
        logging.info('Não esta na tela de resultados...')
        exit

    logging.info('telaRelatorioFinal')

    div_body = page.query_selector_all('.ronaldo .body-resultado')
    itens = []
    ncms = []

    for div_item_body in div_body:
        item = []
        div_item = div_item_body.as_element()
        colunas = div_item.query_selector_all('.produtoa,.ncma')

        for coluna in colunas:
            col = coluna.as_element()

            if 'produtoa' in col.get_attribute('class'):
                itens_p = col.query_selector_all('p')
                ncms = []

                for it in itens_p:
                    ncms.append(str(it.inner_text()).replace(
                        '.', '').replace(',', '.'))

            else:
                item.append(str(col.inner_text()).replace(
                    "R$\xa0", '').replace('\ni', ''))

        if len(ncms) > 0:
            item_completo = []
            item_completo = item.copy()
            item_completo.append(ncms[0])
            item_completo.append(cd_prod)
            item_completo.append(cd_nf)

            # valores
            item_completo[0] = item_completo[0].replace('.', '')
            item_completo[2] = item_completo[2].replace('.', '')
            item_completo[5] = item_completo[5].replace('.', '')
            item_completo[6] = item_completo[6].replace('.', '')
            item_completo[7] = item_completo[7].replace('.', '')
            item_completo[8] = item_completo[8].replace('.', '')
            item_completo[9] = item_completo[9].replace('.', '')
            item_completo[10] = item_completo[10].replace('.', '')
            item_completo[11] = item_completo[11].replace('.', '')
            item_completo[12] = item_completo[12].replace('.', '')

            item_completo.append(cd_filial)
            item_completo.append(num_item)

            itens.append(item_completo)

    if (len(itens) > 0):
        insertDataTable(itens)


def processarItem(page: Page, ncm, cest,  vlr_unit, vlr_ipi, qtd, vlr_frete, perc_fcp,
                  aliq_interna_dest, perc_redu, perc_desc, origem):
    logging.info('processarItens')

    if tela_mercadorias(page, ncm, cest):
        telaDadosDoItem(page,  vlr_unit, vlr_ipi, qtd,
                        vlr_frete, perc_fcp, aliq_interna_dest, perc_redu, perc_desc, origem)


def processarCabecalho(page: Page, ncm_db, text_origem, text_destino,
                       text_complementar, text_tp_operacao):

    logging.info('processarCabecalho')
    page.wait_for_timeout(1000)
    page.goto(os.environ['URL_CALCULO'])
    # selecionar tipo de operação
    tp_operacao = page.locator(
        '//*[@id="simuladorCalculo"]/form[1]/div/div/input')
    tp_operacao.click()
    page.click(
        f'ul.el-scrollbar__view.el-select-dropdown__list li:has-text("{text_tp_operacao}")')

    # origem =--------------------------------
    origem = page.locator(
        '//*[@id="simuladorCalculo"]/form[2]/div[1]/div/div/div/input')
    origem.click()

    page.wait_for_timeout(1000)
    li_selector = 'body > div:nth-child(9) > div.el-scrollbar > div.el-select-dropdown__wrap.el-scrollbar__wrap > ul li'
    li_elements = page.query_selector_all(li_selector)

    for li_element in li_elements:
        text_content = li_element.inner_text()

        if text_origem in text_content:
            li_element.click()
            break
    else:
        logging.info('elemento de origem de estado não encontrado')
        raise RuntimeError('elemento de origem de estado não encontrado')
    # ---------------------------------------
    destino = page.locator(
        '//*[@id="simuladorCalculo"]/form[2]/div[2]/div/div/div/input')
    destino.click()

    page.wait_for_timeout(1000)
    li_selector = 'body > div:nth-child(10) > div.el-scrollbar > div.el-select-dropdown__wrap.el-scrollbar__wrap > ul li'
    li_elements = page.query_selector_all(li_selector)

    for li_element in li_elements:
        text_content = li_element.inner_text()

        if text_destino in text_content:
            li_element.click()
            break
    else:
        logging.info('Elemento de destino de estado não encontrado.')
        raise RuntimeError('Elemento de destino de estado não encontrado.')

    # -----
    info_complementar = page.locator(
        ' //*[@id="simuladorCalculo"]/div[5]/div/input')
    info_complementar.click()

    page.wait_for_timeout(1000)
    li_selector = 'body > div:nth-child(11) > div.el-scrollbar > div.el-select-dropdown__wrap.el-scrollbar__wrap > ul li'
    li_elements = page.query_selector_all(li_selector)

    for li_element in li_elements:
        text_content = li_element.inner_text()

        if text_complementar in text_content:
            li_element.click()
            break
    else:
        logging.info('elemento de texto complementar não encontrado')
        raise RuntimeError('elemento de texto complementar não encontrado')

    ncm = page.locator(
        '//*[@id="simuladorCalculo"]/div[8]/input')
    ncm.fill(ncm_db[:4])

    buscar = page.locator('.btnBuscar')
    buscar.click()


def main():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Abrir o Google
        page.goto(os.environ['URL_BASE'])

        # Localizar o botão usando um seletor CSS
        button = page.locator('//*[@id="app"]/div/header/div/nav/button')
        button.click()

        # Usar XPath para localizar o campo de entrada (substitua o XPath com o correto)
        input_field = page.locator(
            '//*[@id="username"]')
        input_field.fill(os.environ['USUARIO_LEFISC'])

        input_field = page.locator(
            '//*[@id="password"]')
        input_field.fill(os.environ['SENHA_LEFISC'])

        button = page.locator(
            'body > div.flex.justify-center.items-center.vfm.vfm--fixed.vfm--inset > div.vfm__content.vfm--outline-none.relative.p-8.rounded.bg-\[\#e8e8e8\] > div.flex.items-center.justify-center > div > form > div.flex.justify-center > button')

        button.click()

        getTasks(page)

        page.wait_for_timeout(1000)
        browser.close()


if __name__ == "__main__":
    while True:
        try:
            main()
            logging.info('aguardando...')
            SendMessageSlack('aguardando... 60 minutos')
        except Exception as error:
            logging.error(error)
            SendMessageSlack('Erro')
            print(error)

        time.sleep(60 * 60)
