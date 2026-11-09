import urllib.request

import fitz

URLS = ["https://images.unsplash.com/photo-1513828583688-c52646db42da?w=800&fm=jpg",
        "https://images.unsplash.com/photo-1513828742140-ccaa28f3eda0?w=800&fm=jpg"]
ITEMS = [("TEST_ AquaFlow 500 Centrifugal Pump", "Stainless steel centrifugal pump for process water. Flow 500 L/min, head 40 m, motor 7.5 kW, 415 V."),
         ("TEST_ SteelLine Piping Skid", "Pre-assembled stainless piping skid with valves and gauges. Pipe size DN80, pressure rating 16 bar.")]

doc = fitz.open()
for (title, desc), url in zip(ITEMS, URLS):
    page = doc.new_page()
    page.insert_text((50, 60), "Test Supplier Co - Product Catalogue 2026", fontsize=14)
    page.insert_image(fitz.Rect(50, 90, 400, 330), stream=urllib.request.urlopen(url).read())
    page.insert_text((50, 360), title, fontsize=16)
    page.insert_textbox(fitz.Rect(50, 375, 550, 480), desc, fontsize=11)
doc.save("/tmp/test_catalogue.pdf")
print("ok")
