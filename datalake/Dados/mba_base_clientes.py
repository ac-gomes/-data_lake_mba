import json
import random
import sys

# ==========================================
# PRIMEIROS NOMES
# ==========================================

nomes = [
    "Andre", "Debora", "Rafael", "Felipe", "Tatiane",
    "Juliana", "Danilo", "Flavia", "Vinicius", "Beatriz",
    "Rodrigo", "Bruna", "Alexandre", "Renata", "Caio",
    "Kelly", "Marcos", "Camila", "Gabriel", "Mariana",
    "Lucas", "Patricia", "Eduardo", "Fernanda", "Ricardo",
    "Aline", "Bruno", "Larissa", "Thiago", "Amanda",
    "Carlos", "Ana", "Pedro", "Maria", "Joao",
    "Julia", "Gustavo", "Leticia", "Leonardo", "Isabela",
    "Matheus", "Carolina", "Diego", "Natalia", "Henrique",
    "Luana", "Fernando", "Bianca", "Marcelo", "Vanessa",
    "Rafael", "Priscila", "Fabio", "Cristina", "Daniel",
    "Monica", "Renan", "Sabrina", "Igor", "Elaine",
    "Alex", "Simone", "Victor", "Raquel", "Wesley",
    "Claudia", "Samuel", "Adriana", "Murilo", "Tatiana",
    "Vitor", "Carla", "Otavio", "Regina", "Arthur",
    "Manuela", "Enzo", "Helena", "Miguel", "Laura",
    "Davi", "Valentina", "Nicolas", "Alice", "Bernardo",
    "Sophia", "Theo", "Livia", "Heitor", "Melissa"
]

# ==========================================
# SOBRENOMES
# ==========================================

sobrenomes = [
    "Silva", "Santos", "Oliveira", "Souza", "Pereira",
    "Costa", "Rodrigues", "Almeida", "Nascimento", "Lima",
    "Araujo", "Fernandes", "Carvalho", "Gomes", "Martins",
    "Rocha", "Ribeiro", "Alves", "Monteiro", "Mendes",
    "Barbosa", "Freitas", "Barros", "Dias", "Castro",
    "Cardoso", "Teixeira", "Moreira", "Correia", "Moura",
    "Cavalcanti", "Pinto", "Ramos", "Macedo", "Miranda",
    "Nunes", "Machado", "Batista", "Marques", "Duarte",
    "Tavares", "Vieira", "Coelho", "Sales", "Farias",
    "Campos", "Andrade", "Borges", "Moraes", "Cunha",
    "Melo", "Guimaraes", "Bezerra", "Queiroz", "Rezende",
    "Medeiros", "Siqueira", "Vasconcelos", "Amaral", "Braga"
]

# ==========================================
# CIDADES BRASILEIRAS
# ==========================================

cidades = [

    # São Paulo
    ("São Paulo", "SP"),
    ("Guarulhos", "SP"),
    ("Campinas", "SP"),
    ("São Bernardo do Campo", "SP"),
    ("Santo André", "SP"),
    ("Osasco", "SP"),
    ("São José dos Campos", "SP"),
    ("Ribeirão Preto", "SP"),
    ("Sorocaba", "SP"),
    ("Santos", "SP"),
    ("Mauá", "SP"),
    ("São José do Rio Preto", "SP"),
    ("Mogi das Cruzes", "SP"),
    ("Piracicaba", "SP"),
    ("Jundiaí", "SP"),
    ("Bauru", "SP"),
    ("São Vicente", "SP"),
    ("Franca", "SP"),
    ("Guarujá", "SP"),
    ("Taubaté", "SP"),
    ("Praia Grande", "SP"),
    ("Limeira", "SP"),
    ("Suzano", "SP"),
    ("Taboão da Serra", "SP"),
    ("Barueri", "SP"),
    ("Embu das Artes", "SP"),
    ("Itu", "SP"),
    ("Americana", "SP"),
    ("Indaiatuba", "SP"),
    ("Cotia", "SP"),
    ("Santana de Parnaíba", "SP"),

    # Rio de Janeiro
    ("Rio de Janeiro", "RJ"),
    ("Niterói", "RJ"),
    ("São Gonçalo", "RJ"),
    ("Duque de Caxias", "RJ"),
    ("Nova Iguaçu", "RJ"),
    ("Petrópolis", "RJ"),
    ("Volta Redonda", "RJ"),
    ("Campos dos Goytacazes", "RJ"),
    ("Macaé", "RJ"),
    ("Cabo Frio", "RJ"),
    ("Angra dos Reis", "RJ"),
    ("Belford Roxo", "RJ"),
    ("Itaboraí", "RJ"),
    ("Resende", "RJ"),

    # Minas Gerais
    ("Belo Horizonte", "MG"),
    ("Uberlândia", "MG"),
    ("Contagem", "MG"),
    ("Juiz de Fora", "MG"),
    ("Betim", "MG"),
    ("Montes Claros", "MG"),
    ("Uberaba", "MG"),
    ("Governador Valadares", "MG"),
    ("Ipatinga", "MG"),
    ("Poços de Caldas", "MG"),
    ("Divinópolis", "MG"),
    ("Ouro Preto", "MG"),
    ("Sete Lagoas", "MG"),

    # Paraná
    ("Curitiba", "PR"),
    ("Londrina", "PR"),
    ("Maringá", "PR"),
    ("Ponta Grossa", "PR"),
    ("Cascavel", "PR"),
    ("São José dos Pinhais", "PR"),
    ("Foz do Iguaçu", "PR"),
    ("Colombo", "PR"),
    ("Guarapuava", "PR"),
    ("Paranaguá", "PR"),
    ("Araucária", "PR"),

    # Santa Catarina
    ("Florianópolis", "SC"),
    ("Joinville", "SC"),
    ("Blumenau", "SC"),
    ("São José", "SC"),
    ("Chapecó", "SC"),
    ("Itajaí", "SC"),
    ("Criciúma", "SC"),
    ("Jaraguá do Sul", "SC"),
    ("Lages", "SC"),
    ("Balneário Camboriú", "SC"),
    ("Brusque", "SC"),

    # Rio Grande do Sul
    ("Porto Alegre", "RS"),
    ("Caxias do Sul", "RS"),
    ("Canoas", "RS"),
    ("Pelotas", "RS"),
    ("Santa Maria", "RS"),
    ("Novo Hamburgo", "RS"),
    ("São Leopoldo", "RS"),
    ("Rio Grande", "RS"),
    ("Passo Fundo", "RS"),
    ("Gramado", "RS"),

    # Bahia
    ("Salvador", "BA"),
    ("Feira de Santana", "BA"),
    ("Vitória da Conquista", "BA"),
    ("Camaçari", "BA"),
    ("Juazeiro", "BA"),
    ("Ilhéus", "BA"),
    ("Itabuna", "BA"),
    ("Porto Seguro", "BA"),
    ("Barreiras", "BA"),

    # Pernambuco
    ("Recife", "PE"),
    ("Jaboatão dos Guararapes", "PE"),
    ("Olinda", "PE"),
    ("Caruaru", "PE"),
    ("Petrolina", "PE"),
    ("Paulista", "PE"),
    ("Cabo de Santo Agostinho", "PE"),
    ("Garanhuns", "PE"),

    # Ceará
    ("Fortaleza", "CE"),
    ("Caucaia", "CE"),
    ("Juazeiro do Norte", "CE"),
    ("Maracanaú", "CE"),
    ("Sobral", "CE"),
    ("Crato", "CE"),
    ("Itapipoca", "CE"),

    # Goiás
    ("Goiânia", "GO"),
    ("Aparecida de Goiânia", "GO"),
    ("Anápolis", "GO"),
    ("Rio Verde", "GO"),
    ("Luziânia", "GO"),
    ("Águas Lindas de Goiás", "GO"),
    ("Catalão", "GO"),

    # Distrito Federal
    ("Brasília", "DF"),

    # Espírito Santo
    ("Vitória", "ES"),
    ("Vila Velha", "ES"),
    ("Serra", "ES"),
    ("Cariacica", "ES"),
    ("Linhares", "ES"),
    ("Cachoeiro de Itapemirim", "ES"),

    # Pará
    ("Belém", "PA"),
    ("Ananindeua", "PA"),
    ("Santarém", "PA"),
    ("Marabá", "PA"),
    ("Parauapebas", "PA"),

    # Amazonas
    ("Manaus", "AM"),
    ("Parintins", "AM"),
    ("Itacoatiara", "AM"),

    # Maranhão
    ("São Luís", "MA"),
    ("Imperatriz", "MA"),
    ("Timon", "MA"),
    ("Caxias", "MA"),

    # Paraíba
    ("João Pessoa", "PB"),
    ("Campina Grande", "PB"),
    ("Santa Rita", "PB"),
    ("Patos", "PB"),

    # Rio Grande do Norte
    ("Natal", "RN"),
    ("Mossoró", "RN"),
    ("Parnamirim", "RN"),
    ("São Gonçalo do Amarante", "RN"),

    # Alagoas
    ("Maceió", "AL"),
    ("Arapiraca", "AL"),
    ("Rio Largo", "AL"),

    # Mato Grosso
    ("Cuiabá", "MT"),
    ("Várzea Grande", "MT"),
    ("Rondonópolis", "MT"),
    ("Sinop", "MT"),

    # Mato Grosso do Sul
    ("Campo Grande", "MS"),
    ("Dourados", "MS"),
    ("Três Lagoas", "MS"),
    ("Corumbá", "MS"),

    # Piauí
    ("Teresina", "PI"),
    ("Parnaíba", "PI"),
    ("Picos", "PI"),

    # Sergipe
    ("Aracaju", "SE"),
    ("Nossa Senhora do Socorro", "SE"),
    ("Lagarto", "SE"),

    # Rondônia
    ("Porto Velho", "RO"),
    ("Ji-Paraná", "RO"),
    ("Ariquemes", "RO"),

    # Tocantins
    ("Palmas", "TO"),
    ("Araguaína", "TO"),
    ("Gurupi", "TO"),

    # Acre
    ("Rio Branco", "AC"),
    ("Cruzeiro do Sul", "AC"),

    # Amapá
    ("Macapá", "AP"),
    ("Santana", "AP"),

    # Roraima
    ("Boa Vista", "RR"),

    # Rondônia
    ("Porto Velho", "RO"),
]


# ==========================================
# GERADOR
# ==========================================

def gerar_clientes(quantidade, arquivo="clientes.json"):

    with open(arquivo, "w", encoding="utf-8") as f:

        for i in range(quantidade):

            nome = random.choice(nomes)
            sobrenome = random.choice(sobrenomes)

            cidade, estado = random.choice(cidades)

            cliente = {
                "cliente_id": 505 + i,
                "nome": f"{nome} {sobrenome}",
                "cidade": cidade,
                "estado": estado
            }

            f.write(
                json.dumps(
                    cliente,
                    ensure_ascii=False
                ) + "\n"
            )

    print()
    print("==========================================")
    print("   GERADOR DE CLIENTES")
    print("==========================================")
    print(f"Registros gerados : {quantidade}")
    print(f"ID inicial        : 505")
    print(f"ID final          : {504 + quantidade}")
    print(f"Arquivo           : {arquivo}")
    print("==========================================")


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Uso:")
        print("  python gerar_clientes.py <quantidade>")
        print()
        print("Exemplos:")
        print("  python gerar_clientes.py 1000")
        print("  python gerar_clientes.py 10000")
        print("  python gerar_clientes.py 100000 clientes.json")

        sys.exit(1)

    quantidade = int(sys.argv[1])

    arquivo = "clientes.json"

    if len(sys.argv) >= 3:
        arquivo = sys.argv[2]

    gerar_clientes(quantidade, arquivo)
