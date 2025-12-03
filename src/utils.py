import re

def clean_text_for_tts(text):
    # 1. Тусгай тэмдэгтүүдийг Монгол үгээр солих
    text = text.replace("%", " хувь")
    text = text.replace("$", " доллар")
    text = text.replace("₮", " төгрөг")
    text = text.replace("&", " ба")
    text = text.replace("+", " нэмэх")
    text = text.replace("=", " тэнцүү")
    text = text.replace("/", " хуваах")
    text = text.replace("*", " үржих")
    text = text.replace("@", " эт")
    
    # 2. Markdown тэмдэглэгээг устгах (bold, italic, headers)
    text = text.replace("*", "")
    text = text.replace("_", "")
    text = text.replace("#", "")
    
    # 3. Хаалтан доторх агуулгыг устгах
    text = re.sub(r'\([^)]*\)', '', text)
    
    # 4. Тоог үг рүү хөрвүүлэх (Бүрэн хувилбар)
    # Тоон доторх таслалыг устгах (Жишээ нь: 252,500 -> 252500)
    text = re.sub(r'(\d),(\d)', r'\1\2', text)

    def number_to_mongolian_text(n):
        if n == 0: return "тэг"
        
        units = ["", "нэг", "хоёр", "гурав", "дөрөв", "тав", "зургаа", "долоо", "найм", "ес"]
        tens = ["", "арав", "хорин", "гучин", "дөчин", "тавин", "жаран", "далан", "наян", "ерөн"]
        
        def convert_chunk(num):
            if num == 0: return ""
            s = ""
            # Зуут
            h = num // 100
            if h > 0:
                if h == 1: s += "зуун "
                else: s += units[h] + " зуун "
            
            # Аравт ба Нэгж
            rem = num % 100
            if rem > 0:
                if rem < 10:
                    s += units[rem] + " "
                else:
                    t = rem // 10
                    u = rem % 10
                    if u == 0: s += tens[t] + " "
                    else: s += tens[t] + " " + units[u] + " "
            return s

        parts = []
        # Тэрбум
        b = n // 1000000000
        if b > 0: parts.append(convert_chunk(b) + "тэрбум")
        n %= 1000000000
        
        # Сая
        m = n // 1000000
        if m > 0: parts.append(convert_chunk(m) + "сая")
        n %= 1000000
        
        # Мянга
        k = n // 1000
        if k > 0: 
            if k == 1 and not parts: parts.append("мянган") # 1000 -> мянга (нэг мянга гэж хэлэхгүй)
            else: parts.append(convert_chunk(k) + "мянган")
        n %= 1000
        
        # Үлдэгдэл
        if n > 0: parts.append(convert_chunk(n))
        
        return " ".join(parts).strip()

    def replace_numbers(match):
        try:
            num = int(match.group(0))
            return number_to_mongolian_text(num)
        except:
            return match.group(0)

    text = re.sub(r'\d+', replace_numbers, text)

    # 5. Хоосон зайг цэгцлэх (newline/tab-ийг зайгаар солих)
    text = " ".join(text.split())

    # 6. Хатуу зөвшөөрөгдсөн жагсаалт
    # Зөвшөөрөгдсөн: Кирилл үсэг (А-Яа-яӨөҮүЁё), зай, ?, !, ., -, ', ", :, ,
    # Энэ жагсаалтад байхгүй бүх тэмдэгтийг устгана
    # Тоонуудыг хөрвүүлсэн тул жагсаалтаас хассан
    allowed_pattern = r'[^А-Яа-яӨөҮүЁё\s\?!\.,:\'"-]'
    text = re.sub(allowed_pattern, '', text)
    
    return text.strip()
