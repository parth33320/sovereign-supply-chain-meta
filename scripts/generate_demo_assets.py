import wave
import struct
from PIL import Image, ImageDraw, ImageFont

def generate_shelf_image():
    # Create 800x600 warehouse shelf image
    img = Image.new("RGB", (800, 600), color=(26, 34, 52))
    draw = ImageDraw.Draw(img)

    # Warehouse background details
    draw.rectangle([0, 0, 800, 60], fill=(17, 22, 34))
    draw.text((30, 20), "WAREHOUSE SECTOR 4 - AISLE 12 CAMERA FEED", fill=(148, 163, 184))

    # Shelving frame (uprights)
    upright_color = (71, 85, 105)
    draw.rectangle([50, 70, 70, 560], fill=upright_color)
    draw.rectangle([730, 70, 750, 560], fill=upright_color)

    # 3 Shelves
    shelves = [
        {"y": 200, "name": "Shelf 1: Microcontrollers 32-bit", "qty": 8, "label": "Microcontrollers [95%]"},
        {"y": 350, "name": "Shelf 2: Copper Wire Spools", "qty": 7, "label": "Copper Spools [85%]"},
        {"y": 500, "name": "Shelf 3: Widget-A", "qty": 1, "label": "Widget-A 12%"}
    ]

    for s in shelves:
        y = s["y"]
        # Shelf beam
        draw.rectangle([50, y, 750, y + 16], fill=(100, 116, 139))
        draw.text((75, y - 24), s["name"], fill=(226, 232, 240))

        # Items on shelf
        item_y = y - 65
        qty = s["qty"]
        if "Widget-A" in s["name"]:
            # Nearly empty shelf: 1 solitary box with red highlight
            draw.rectangle([90, item_y + 15, 160, y - 2], fill=(239, 68, 68), outline=(254, 202, 202), width=2)
            draw.text((95, item_y + 25), "Widget-A", fill=(255, 255, 255))
            # Critical stock label
            draw.rectangle([350, y - 50, 650, y - 10], fill=(56, 18, 22), outline=(239, 68, 68), width=2)
            draw.text((370, y - 40), "CRITICAL: Widget-A 12% - LOW STOCK", fill=(252, 165, 165))
        else:
            # Full shelves
            for i in range(qty):
                bx = 90 + i * 85
                draw.rectangle([bx, item_y, bx + 70, y - 2], fill=(30, 58, 138), outline=(96, 165, 250), width=2)
                draw.text((bx + 10, item_y + 20), "BOX", fill=(191, 219, 254))

    img.save("demo-assets/sample_shelf.jpg", quality=90)
    print("Generated demo-assets/sample_shelf.jpg")

def generate_invoice_image():
    # Create 700x850 clean invoice document
    img = Image.new("RGB", (700, 850), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Header / Branding
    draw.rectangle([0, 0, 700, 110], fill=(241, 245, 249))
    draw.text((40, 30), "INVOICE / BILL OF LADING", fill=(15, 23, 42))
    draw.text((40, 65), "Apex Logistics Global Freight Solutions", fill=(71, 85, 105))

    # Metadata Grid
    draw.line([(40, 130), (660, 130)], fill=(203, 213, 225), width=2)
    draw.text((40, 150), "Supplier: Apex Logistics", fill=(15, 23, 42))
    draw.text((40, 180), "Invoice Number: INV-2026-88219", fill=(71, 85, 105))
    draw.text((40, 210), "Invoice Date: 2026-11-04", fill=(15, 23, 42))

    draw.text((400, 150), "Customer: Sovereign Supply Chain", fill=(15, 23, 42))
    draw.text((400, 180), "Tenant Account: Tenant_A", fill=(71, 85, 105))
    draw.text((400, 210), "Payment Terms: Net 30", fill=(71, 85, 105))

    # Table Header
    draw.rectangle([40, 260, 660, 300], fill=(30, 41, 59))
    draw.text((55, 272), "Line", fill=(255, 255, 255))
    draw.text((120, 272), "Description / SKU", fill=(255, 255, 255))
    draw.text((360, 272), "Qty", fill=(255, 255, 255))
    draw.text((450, 272), "Unit Price", fill=(255, 255, 255))
    draw.text((560, 272), "Total Amount", fill=(255, 255, 255))

    # Table Row: Widget-A
    draw.line([(40, 350), (660, 350)], fill=(226, 232, 240), width=1)
    draw.text((55, 320), "01", fill=(71, 85, 105))
    draw.text((120, 320), "Item: Widget-A", fill=(15, 23, 42))
    draw.text((360, 320), "500", fill=(15, 23, 42))
    draw.text((450, 320), "$8.20", fill=(15, 23, 42))
    draw.text((560, 320), "$4,100.00", fill=(15, 23, 42))

    # Summary box
    draw.line([(40, 480), (660, 480)], fill=(203, 213, 225), width=2)
    draw.text((450, 500), "Subtotal:", fill=(71, 85, 105))
    draw.text((560, 500), "$4,100.00", fill=(15, 23, 42))
    draw.text((450, 530), "Freight & Handling:", fill=(71, 85, 105))
    draw.text((560, 530), "$150.00", fill=(15, 23, 42))
    draw.text((450, 565), "Total Due:", fill=(15, 23, 42))
    draw.text((560, 565), "$4,250.00", fill=(15, 23, 42))

    # Footer note
    draw.rectangle([40, 680, 660, 780], fill=(248, 250, 252), outline=(226, 232, 240))
    draw.text((60, 700), "Delivery Instructions: Expedited ground dispatch to Central Distribution Hub.", fill=(100, 116, 139))
    draw.text((60, 730), "Confirmed by: Apex Logistics Supplier AI Autonomous Procurement", fill=(100, 116, 139))

    img.save("demo-assets/sample_invoice.png")
    print("Generated demo-assets/sample_invoice.png")

def generate_voice_placeholder():
    # 3 seconds silence WAV (16kHz, 16-bit mono)
    sample_rate = 16000
    duration_secs = 3
    num_samples = sample_rate * duration_secs

    with wave.open("demo-assets/sample_voice_command.wav", "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        # write 0s
        data = struct.pack(f"<{num_samples}h", *([0] * num_samples))
        wav_file.writeframes(data)
    print("Generated demo-assets/sample_voice_command.wav")

if __name__ == "__main__":
    generate_shelf_image()
    generate_invoice_image()
    generate_voice_placeholder()
