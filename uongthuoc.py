import sys
import cv2
import mediapipe as mp
import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import threading
from gtts import gTTS
import os
import tempfile
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import pygame
import time
import locale
import imageio  # Thêm thư viện imageio
import logging
locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')


class ThanhTieuDeHienDai(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        bo_cuc = QHBoxLayout(self)
        bo_cuc.setContentsMargins(0, 0, 0, 0)

        # Logo và tiêu đề
        bo_cuc_logo = QHBoxLayout()

        nhan_logo = QLabel("💊")
        nhan_logo.setStyleSheet("font-size: 32px; padding: 10px;")

        tieu_de = QLabel("Ứng Dụng Nhắc Nhở Uống Thuốc")
        tieu_de.setStyleSheet("""
            color: #2C3E50;
            font-size: 28px;
            font-weight: bold;
            padding: 10px;
            font-family: 'Arial', sans-serif;
        """)

        # Thêm các widget vào bố cục
        bo_cuc_logo.addWidget(nhan_logo)
        bo_cuc_logo.addWidget(tieu_de)
        bo_cuc.addLayout(bo_cuc_logo)
        bo_cuc.addStretch()

        # Thêm đồng hồ
        self.nhan_thoi_gian = QLabel()
        self.nhan_thoi_gian.setStyleSheet("""
            color: #34495e;
            font-size: 20px;
            padding: 10px;
            font-weight: bold;
        """)
        self.cap_nhat_thoi_gian()

        # Bộ đếm thời gian để cập nhật thời gian
        bo_dem_thoi_gian = QTimer(self)
        bo_dem_thoi_gian.timeout.connect(self.cap_nhat_thoi_gian)
        bo_dem_thoi_gian.start(1000)

        bo_cuc.addWidget(self.nhan_thoi_gian)

    def cap_nhat_thoi_gian(self):
        thoi_gian_hien_tai = QTime.currentTime()
        ngay_hien_tai = QDate.currentDate()
        dinh_dang_thoi_gian = f"{ngay_hien_tai.toString('dd/MM/yyyy')} {thoi_gian_hien_tai.toString('HH:mm:ss')}"
        self.nhan_thoi_gian.setText(dinh_dang_thoi_gian)


class NutXoa(QPushButton):
    da_xoa = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none;
                border-radius: 18px;
                color: white;
                font-weight: bold;
                font-size: 20px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.setText("×")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.emit_da_xoa)

    def emit_da_xoa(self):
        self.da_xoa.emit()


class TheThuocHienDai(QWidget):
    da_xoa = pyqtSignal(int)

    def __init__(self, thuoc, chi_so, parent=None):
        super().__init__(parent)
        self.thuoc = thuoc
        self.chi_so = chi_so
        self.tao_giao_dien()

    def tao_giao_dien(self):
        bo_cuc = QHBoxLayout(self)
        bo_cuc.setContentsMargins(10, 5, 10, 5)

        # Khung thẻ
        the = QFrame()
        the.setObjectName("theThuoc")
        bo_cuc_the = QHBoxLayout(the)

        # Biểu tượng với nền gradient
        khung_bieu_tuong = QFrame()
        khung_bieu_tuong.setFixedSize(50, 50)
        khung_bieu_tuong.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #3498db, stop:1 #2980b9);
                border-radius: 25px;
            }
        """)
        bo_cuc_bieu_tuong = QHBoxLayout(khung_bieu_tuong)
        bo_cuc_bieu_tuong.setContentsMargins(0, 0, 0, 0)

        bieu_tuong = QLabel("💊")
        bieu_tuong.setStyleSheet("color: white; font-size: 24px;")
        bieu_tuong.setAlignment(Qt.AlignCenter)
        bo_cuc_bieu_tuong.addWidget(bieu_tuong)

        bo_cuc_the.addWidget(khung_bieu_tuong)

        # Thông tin thuốc
        widget_thong_tin = QWidget()
        bo_cuc_thong_tin = QVBoxLayout(widget_thong_tin)
        bo_cuc_thong_tin.setSpacing(5)

        nhan_ten = QLabel(self.thuoc["ten"])
        nhan_ten.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            font-family: 'Arial', sans-serif;
        """)

        nhan_thoi_gian = QLabel(self.thuoc["thoi_gian"])
        nhan_thoi_gian.setStyleSheet("""
            font-size: 16px;
            color: #7f8c8d;
        """)

        bo_cuc_thong_tin.addWidget(nhan_ten)
        bo_cuc_thong_tin.addWidget(nhan_thoi_gian)
        bo_cuc_the.addWidget(widget_thong_tin)
        bo_cuc_the.addStretch()

        # Trạng thái với văn bản
        widget_trang_thai = QWidget()
        bo_cuc_trang_thai = QHBoxLayout(widget_trang_thai)

        trang_thai = QFrame()
        trang_thai.setFixedSize(12, 12)
        thoi_gian_hien_tai = QTime.currentTime().toString("HH:mm")
        mau_trang_thai = "#2ecc71" if self.thuoc["thoi_gian"] > thoi_gian_hien_tai else "#e74c3c"
        van_ban_trang_thai = "Sắp đến giờ" if self.thuoc["thoi_gian"] > thoi_gian_hien_tai else "Đã qua giờ"

        trang_thai.setStyleSheet(f"""
            background-color: {mau_trang_thai};
            border-radius: 6px;
        """)

        nhan_trang_thai = QLabel(van_ban_trang_thai)
        nhan_trang_thai.setStyleSheet("""
            color: #7f8c8d;
            font-size: 14px;
            margin-left: 5px;
            font-family: 'Arial', sans-serif;
        """)

        bo_cuc_trang_thai.addWidget(trang_thai)
        bo_cuc_trang_thai.addWidget(nhan_trang_thai)
        bo_cuc_the.addLayout(bo_cuc_trang_thai)

        # Biểu tượng trạng thái uống thuốc
        self.nhan_trang_thai_uong = QLabel()
        self.nhan_trang_thai_uong.setFixedSize(24, 24)
        bo_cuc_the.addWidget(self.nhan_trang_thai_uong)
        self.cap_nhat_trang_thai_uong()  # Cập nhật biểu tượng trạng thái

        # Nút xóa
        nut_xoa = NutXoa()
        nut_xoa.setToolTip("Xóa thuốc này")
        nut_xoa.da_xoa.connect(lambda: self.da_xoa.emit(self.chi_so))
        bo_cuc_the.addWidget(nut_xoa)

        bo_cuc.addWidget(the)

        # Hiệu ứng đổ bóng
        hieu_ung_bong = QGraphicsDropShadowEffect(self)
        hieu_ung_bong.setBlurRadius(15)
        hieu_ung_bong.setXOffset(0)
        hieu_ung_bong.setYOffset(2)
        hieu_ung_bong.setColor(QColor(0, 0, 0, 30))
        the.setGraphicsEffect(hieu_ung_bong)

        the.setStyleSheet("""
            QFrame#theThuoc {
                background-color: white;
                border-radius: 15px;
                padding: 15px;
                border: 1px solid #E0E0E0;
            }
            QFrame#theThuoc:hover {
                background-color: #f8f9fa;
                border: 1px solid #3498db;
            }
        """)

    def cap_nhat_trang_thai_uong(self):
        """Cập nhật biểu tượng trạng thái uống thuốc"""
        trang_thai = self.thuoc.get('trang_thai')
        if trang_thai == 'da_uong':
            icon = QIcon('tick.png')  # Đường dẫn đến biểu tượng dấu tích xanh
            self.nhan_trang_thai_uong.setPixmap(icon.pixmap(24, 24))
        elif trang_thai == 'khong_uong':
            icon = QIcon('nhan.png')  # Đường dẫn đến biểu tượng dấu nhân đỏ
            self.nhan_trang_thai_uong.setPixmap(icon.pixmap(24, 24))
        else:
            self.nhan_trang_thai_uong.clear()


class UngDungNhacNhoUongThuocHienDai(QMainWindow):
    bat_dau_camera_signal = pyqtSignal()
    dung_camera_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("pill.png"))  # Thêm biểu tượng nếu có
        self.setWindowTitle("Ứng Dụng Nhắc Nhở Uống Thuốc")
        self.setGeometry(100, 100, 1200, 800)

        # Biến
        self.danh_sach_thuoc = []
        self.camera_dang_hoat_dong = False
        self.dem_tay = 0
        self.thoi_gian_tay_cuoi = 0
        self.thuoc_hien_tai = None
        self.tay_gan_mieng_truoc = False  # Trạng thái phát hiện tay
        self.phat_hien_khuon_mat = False
        self.thoi_gian_bat_dau_phat_hien_khuon_mat = None
        self.che_do_canh_bao = False  # Chế độ cảnh báo
        self.thoi_gian_cho_canh_bao = 3  # Thời gian chờ trước khi bật cảnh báo (giây)
        self.da_gui_email = False  # Trạng thái đã gửi email cảnh báo
        self.danh_sach_thuoc_da_nhac = []  # Danh sách thuốc đã được nhắc trong ngày

        # Thông tin email
        self.gmail_nguoi_gui = 'canhbaohoctap@gmail.com'
        self.gmail_mat_khau = 'rsvn gqco gqly szzs'
        self.gmail_nguoi_nhan = 'dangphan11108@gmail.com'

        # Khởi tạo MediaPipe
        self.mp_hands = mp.solutions.hands
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Khởi tạo pygame mixer
        pygame.mixer.init()
        print("Pygame mixer đã được khởi tạo.")

        self.tao_giao_dien()
        self.tai_danh_sach_thuoc()

        # Bộ đếm thời gian để kiểm tra thời gian uống thuốc
        self.bo_dem_thoi_gian = QTimer(self)
        self.bo_dem_thoi_gian.timeout.connect(self.kiem_tra_thoi_gian_thuoc)
        self.bo_dem_thoi_gian.start(1000)

        # Bắt đầu luồng reset hàng ngày
        self.bat_dau_luong_reset_hang_ngay()

    def tao_giao_dien(self):
        widget_trung_tam = QWidget()
        self.setCentralWidget(widget_trung_tam)
        bo_cuc_chinh = QVBoxLayout(widget_trung_tam)
        bo_cuc_chinh.setContentsMargins(0, 0, 0, 0)
        bo_cuc_chinh.setSpacing(0)

        # Thanh tiêu đề
        thanh_tieu_de = ThanhTieuDeHienDai()
        bo_cuc_chinh.addWidget(thanh_tieu_de)

        # Nội dung
        noi_dung = QWidget()
        bo_cuc_noi_dung = QHBoxLayout(noi_dung)
        bo_cuc_noi_dung.setContentsMargins(20, 20, 20, 20)
        bo_cuc_noi_dung.setSpacing(20)

        # Panel bên trái - Thêm thuốc
        panel_trai = self.tao_panel_trai()

        # Panel bên phải - Danh sách thuốc
        panel_phai = self.tao_panel_phai()

        # Thêm các panel vào nội dung
        bo_cuc_noi_dung.addWidget(panel_trai)
        bo_cuc_noi_dung.addWidget(panel_phai)
        bo_cuc_chinh.addWidget(noi_dung)

        self.ap_dung_phong_cach()

    def tao_panel_trai(self):
        panel_trai = QWidget()
        panel_trai.setFixedWidth(400)
        panel_trai.setObjectName("panelTrai")
        bo_cuc_trai = QVBoxLayout(panel_trai)

        # Container form
        widget_form = QWidget()
        widget_form.setObjectName("widgetForm")
        bo_cuc_form = QVBoxLayout(widget_form)

        # Tiêu đề
        tieu_de = QLabel("Thêm Thuốc Mới")
        tieu_de.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2C3E50;
            margin-bottom: 20px;
            font-family: 'Arial', sans-serif;
        """)

        # Trường nhập liệu
        self.o_nhap_ten = QLineEdit()
        self.o_nhap_ten.setPlaceholderText("Tên thuốc")
        self.o_nhap_ten.setObjectName("oNhapTen")

        self.o_nhap_thoi_gian = QTimeEdit()
        self.o_nhap_thoi_gian.setDisplayFormat("HH:mm")
        self.o_nhap_thoi_gian.setObjectName("oNhapThoiGian")
        self.o_nhap_thoi_gian.setTime(QTime.currentTime())

        # Nút
        container_nut = QWidget()
        bo_cuc_nut = QHBoxLayout(container_nut)

        nut_them = QPushButton("Thêm Thuốc")
        nut_them.setObjectName("nutThem")
        nut_them.setCursor(Qt.PointingHandCursor)
        nut_them.clicked.connect(self.them_thuoc)

        nut_xoa_tat_ca = QPushButton("Xóa Tất Cả")
        nut_xoa_tat_ca.setObjectName("nutXoaTatCa")
        nut_xoa_tat_ca.setCursor(Qt.PointingHandCursor)
        nut_xoa_tat_ca.clicked.connect(self.xoa_tat_ca_thuoc)

        bo_cuc_nut.addWidget(nut_them)
        bo_cuc_nut.addWidget(nut_xoa_tat_ca)

        # Thêm widget vào form
        bo_cuc_form.addWidget(tieu_de)
        bo_cuc_form.addWidget(QLabel("Tên thuốc:"))
        bo_cuc_form.addWidget(self.o_nhap_ten)
        bo_cuc_form.addWidget(QLabel("Thời gian:"))
        bo_cuc_form.addWidget(self.o_nhap_thoi_gian)
        bo_cuc_form.addWidget(container_nut)
        bo_cuc_form.addStretch()

        # Thêm thống kê
        widget_thong_ke = self.tao_widget_thong_ke()
        bo_cuc_form.addWidget(widget_thong_ke)

        bo_cuc_trai.addWidget(widget_form)
        return panel_trai

    def xoa_tat_ca_thuoc(self):
        if not self.danh_sach_thuoc:
            return

        self.danh_sach_thuoc.clear()
        self.cap_nhat_danh_sach_thuoc()
        self.luu_danh_sach_thuoc()

    def xoa_thuoc(self, chi_so):
        """Xóa một thuốc khỏi danh sách"""
        if 0 <= chi_so < len(self.danh_sach_thuoc):
            del self.danh_sach_thuoc[chi_so]
            self.cap_nhat_danh_sach_thuoc()
            self.luu_danh_sach_thuoc()

    def tao_panel_phai(self):
        panel_phai = QWidget()
        panel_phai.setObjectName("panelPhai")
        bo_cuc_phai = QVBoxLayout(panel_phai)

        # Header
        tieu_de = QWidget()
        bo_cuc_tieu_de = QHBoxLayout(tieu_de)

        tieu_de_danh_sach = QLabel("Danh Sách Thuốc")
        tieu_de_danh_sach.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2C3E50;
            font-family: 'Arial', sans-serif;
        """)

        o_tim_kiem = QLineEdit()
        o_tim_kiem.setPlaceholderText("Tìm kiếm thuốc...")
        o_tim_kiem.setObjectName("oTimKiem")
        o_tim_kiem.textChanged.connect(self.loc_danh_sach_thuoc)

        bo_cuc_tieu_de.addWidget(tieu_de_danh_sach)
        bo_cuc_tieu_de.addWidget(o_tim_kiem)

        # Danh sách thuốc
        self.khu_vuc_danh_sach_thuoc = QScrollArea()
        self.khu_vuc_danh_sach_thuoc.setWidgetResizable(True)
        self.khu_vuc_danh_sach_thuoc.setObjectName("khuVucDanhSachThuoc")

        self.widget_danh_sach_thuoc = QWidget()
        self.bo_cuc_danh_sach_thuoc = QVBoxLayout(self.widget_danh_sach_thuoc)
        self.bo_cuc_danh_sach_thuoc.addStretch()

        self.khu_vuc_danh_sach_thuoc.setWidget(self.widget_danh_sach_thuoc)

        bo_cuc_phai.addWidget(tieu_de)
        bo_cuc_phai.addWidget(self.khu_vuc_danh_sach_thuoc)

        return panel_phai

    def tao_widget_thong_ke(self):
        widget_thong_ke = QWidget()
        widget_thong_ke.setObjectName("widgetThongKe")
        bo_cuc_thong_ke = QVBoxLayout(widget_thong_ke)

        tieu_de = QLabel("Thống kê")
        tieu_de.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2C3E50;
            margin-bottom: 10px;
            font-family: 'Arial', sans-serif;
        """)

        self.tong_so_thuoc = QLabel("Tổng số thuốc: 0")
        self.sap_den_gio = QLabel("Sắp đến giờ: 0")
        self.da_uong_hom_nay = QLabel("Đã uống hôm nay: 0")

        for nhan in [self.tong_so_thuoc, self.sap_den_gio, self.da_uong_hom_nay]:
            nhan.setStyleSheet("""
                font-size: 14px;
                color: #7f8c8d;
                margin: 5px 0;
                font-family: 'Arial', sans-serif;
            """)

        bo_cuc_thong_ke.addWidget(tieu_de)
        bo_cuc_thong_ke.addWidget(self.tong_so_thuoc)
        bo_cuc_thong_ke.addWidget(self.sap_den_gio)
        bo_cuc_thong_ke.addWidget(self.da_uong_hom_nay)

        return widget_thong_ke

    def ap_dung_phong_cach(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F6FA;
            }
            #panelTrai, #panelPhai {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #E0E0E0;
            }
            #widgetForm {
                margin: 20px;
            }
            QLineEdit, QTimeEdit {
                padding: 12px;
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                font-size: 14px;
                margin-bottom: 15px;
            }
            QLineEdit:focus, QTimeEdit:focus {
                border: 2px solid #3498DB;
            }
            #oTimKiem {
                max-width: 300px;
                margin: 0;
            }
            #nutThem {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Arial', sans-serif;
            }
            #nutThem:hover {
                background-color: #2980B9;
            }
            #nutXoaTatCa {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Arial', sans-serif;
            }
            #nutXoaTatCa:hover {
                background-color: #c0392b;
            }
            #widgetThongKe {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 15px;
                margin-top: 20px;
            }
            QLabel {
                font-family: 'Arial', sans-serif;
            }
        """)

    def loc_danh_sach_thuoc(self, text):
        """Lọc danh sách thuốc dựa trên từ khóa tìm kiếm"""
        for i in range(self.bo_cuc_danh_sach_thuoc.count() - 1):
            widget = self.bo_cuc_danh_sach_thuoc.itemAt(i).widget()
            if widget:
                hien_thi = text.lower() in widget.thuoc["ten"].lower()
                widget.setVisible(hien_thi)

    def cap_nhat_thong_ke(self):
        """Cập nhật thống kê"""
        tong = len(self.danh_sach_thuoc)
        thoi_gian_hien_tai = QTime.currentTime()
        sap_den_gio = sum(1 for thuoc in self.danh_sach_thuoc if QTime.fromString(thuoc["thoi_gian"], "HH:mm") > thoi_gian_hien_tai)
        da_uong = sum(1 for thuoc in self.danh_sach_thuoc if self.da_uong_thuoc(thuoc))

        self.tong_so_thuoc.setText(f"Tổng số thuốc: {tong}")
        self.sap_den_gio.setText(f"Sắp đến giờ: {sap_den_gio}")
        self.da_uong_hom_nay.setText(f"Đã uống hôm nay: {da_uong}")

    def them_thuoc(self):
        ten = self.o_nhap_ten.text()
        thoi_gian = self.o_nhap_thoi_gian.time().toString("HH:mm")

        if ten and thoi_gian:
            thuoc = {
                "ten": ten,
                "thoi_gian": thoi_gian,
                "lich_su_uong": [],
                "trang_thai": None  # Trạng thái uống thuốc: None, 'da_uong', 'khong_uong'
            }
            self.danh_sach_thuoc.append(thuoc)
            self.cap_nhat_danh_sach_thuoc()
            self.luu_danh_sach_thuoc()
            self.cap_nhat_thong_ke()

            self.o_nhap_ten.clear()
        else:
            QMessageBox.warning(
                self,
                "Lỗi",
                "Vui lòng nhập đầy đủ tên thuốc và thời gian!",
                QMessageBox.Ok
            )

    def cap_nhat_danh_sach_thuoc(self):
        # Xóa các mục cũ
        for i in reversed(range(self.bo_cuc_danh_sach_thuoc.count())):
            widget = self.bo_cuc_danh_sach_thuoc.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Thêm các thẻ thuốc mới
        for i, thuoc in enumerate(self.danh_sach_thuoc):
            the = TheThuocHienDai(thuoc, i)
            the.da_xoa.connect(self.xoa_thuoc)
            self.bo_cuc_danh_sach_thuoc.insertWidget(
                self.bo_cuc_danh_sach_thuoc.count() - 1,
                the
            )
            # Cập nhật trạng thái uống thuốc
            the.cap_nhat_trang_thai_uong()

        self.cap_nhat_thong_ke()

    def luu_danh_sach_thuoc(self):
        with open("danh_sach_thuoc.json", "w", encoding="utf-8") as f:
            json.dump(self.danh_sach_thuoc, f, ensure_ascii=False, indent=2)

    def tai_danh_sach_thuoc(self):
        try:
            with open("danh_sach_thuoc.json", "r", encoding="utf-8") as f:
                self.danh_sach_thuoc = json.load(f)
                self.cap_nhat_danh_sach_thuoc()
        except FileNotFoundError:
            pass

    def closeEvent(self, event):
        self.luu_danh_sach_thuoc()
        if self.camera_dang_hoat_dong:
            self.dung_camera()
        event.accept()

    def noi_tieng_viet(self, van_ban):
        """Chuyển văn bản thành giọng nói tiếng Việt"""

        def luong_noi():
            try:
                print(f"Đang tạo giọng nói cho văn bản: {van_ban}")
                # Tạo tên tệp tạm thời
                ten_tep_tam = os.path.join(tempfile.gettempdir(), f"{time.time()}_temp.mp3")
                tts = gTTS(text=van_ban, lang='vi')
                tts.save(ten_tep_tam)
                print(f"Đã lưu tệp âm thanh tạm thời tại {ten_tep_tam}")

                # Sử dụng pygame để phát âm thanh
                pygame.mixer.music.load(ten_tep_tam)
                pygame.mixer.music.play()
                print("Đang phát âm thanh...")

                # Chờ đến khi phát xong
                while pygame.mixer.music.get_busy():
                    pygame.time.delay(1)

                print("Đã phát xong âm thanh.")
                # Xóa tệp tạm thời
                pygame.mixer.music.unload()
                os.remove(ten_tep_tam)
                print("Đã xóa tệp âm thanh tạm thời.")
            except Exception as e:
                print(f"Lỗi TTS: {str(e)}")

        luong = threading.Thread(target=luong_noi)
        luong.daemon = True
        luong.start()

    def noi_tieng_viet_lien_tuc(self, van_ban):
        """Thông báo văn bản liên tục trong một luồng riêng."""
        if not hasattr(self, 'luong_canh_bao') or not self.luong_canh_bao.is_alive():
            self.luong_canh_bao = threading.Thread(target=self.vong_lap_canh_bao, args=(van_ban,))
            self.luong_canh_bao.daemon = True
            self.luong_canh_bao.start()

    def vong_lap_canh_bao(self, van_ban):
        start_time = time.time()
        # Chờ 10 giây trước khi bắt đầu nhắc nhở
        while time.time() - start_time < 10:
            if not self.che_do_canh_bao or self.da_uong_thuoc(self.thuoc_hien_tai):
                return
            time.sleep(1)

        # Bắt đầu nhắc nhở
        remind_start_time = time.time()
        while self.che_do_canh_bao and not self.da_uong_thuoc(self.thuoc_hien_tai):
            elapsed_time = time.time() - remind_start_time
            if elapsed_time > self.thoi_gian_cho_canh_bao:
                # Sau 10 giây kể từ khi bắt đầu nhắc nhở, dừng nhắc nhở, tắt camera và đánh dấu là không uống
                self.noi_tieng_viet("Bạn đã không uống thuốc. Kết thúc nhắc nhở.")

                # Gửi email thông báo
                if not self.da_gui_email:
                    tieu_de_email = "Cảnh báo: Không uống thuốc"
                    noi_dung_email = f"Người dùng đã không uống thuốc {self.thuoc_hien_tai['ten']} vào lúc {self.thuoc_hien_tai['thoi_gian']}."
                    self.gui_email(tieu_de_email, noi_dung_email)
                    self.da_gui_email = True

                self.danh_dau_khong_uong_thuoc(self.thuoc_hien_tai)
                self.dung_camera()
                break
            self.noi_tieng_viet(van_ban)
            time.sleep(1)  # Chờ trước khi lặp lại

    def nhac_nho_thuoc(self, thuoc):
        print(f"Nhắc nhở thuốc: {thuoc['ten']} lúc {thuoc['thoi_gian']}")
        self.thuoc_hien_tai = thuoc
        self.che_do_canh_bao = True
        self.phat_hien_khuon_mat = False
        self.thoi_gian_bat_dau_phat_hien_khuon_mat = None
        self.da_gui_email = False

        # Thông báo ngay lập tức
        van_ban = f"Đã đến giờ uống thuốc {self.thuoc_hien_tai['ten']}"
        self.noi_tieng_viet(van_ban)

        # Bắt đầu camera
        if not self.camera_dang_hoat_dong:
            self.bat_dau_camera()

        self.noi_tieng_viet_lien_tuc("Bạn chưa uống thuốc")

    def kiem_tra_thoi_gian_thuoc(self):
        thoi_gian_hien_tai = datetime.datetime.now()
        thoi_gian_hien_tai_str = thoi_gian_hien_tai.strftime("%H:%M")
        ngay_hien_tai_str = thoi_gian_hien_tai.strftime("%Y-%m-%d")
        print(f"Thời gian hiện tại: {thoi_gian_hien_tai_str}")
        for thuoc in self.danh_sach_thuoc:
            thoi_gian_thuoc_str = thuoc["thoi_gian"]
            print(f"Kiểm tra thuốc: {thuoc['ten']} lúc {thoi_gian_thuoc_str}")

            # Tạo một khóa cho mỗi lần nhắc nhở trong ngày
            khoa_nhac_nho = f"{ngay_hien_tai_str}_{thuoc['ten']}_{thoi_gian_thuoc_str}"

            # Kiểm tra nếu thuốc đã đc nhắc trong ngày
            if (thoi_gian_hien_tai_str == thoi_gian_thuoc_str and
                    not self.camera_dang_hoat_dong and
                    not self.da_uong_thuoc(thuoc) and
                    khoa_nhac_nho not in self.danh_sach_thuoc_da_nhac):
                print(f"Kích hoạt nhắc nhở cho {thuoc['ten']}")
                self.danh_sach_thuoc_da_nhac.append(khoa_nhac_nho)
                self.nhac_nho_thuoc(thuoc)
        self.cap_nhat_thong_ke()

    def da_uong_thuoc(self, thuoc):
        ngay_hien_tai = datetime.datetime.now().date().strftime("%Y-%m-%d")
        khoa_uong = f"{ngay_hien_tai}_{thuoc['thoi_gian']}"
        return khoa_uong in thuoc.get('lich_su_uong', [])

    def danh_dau_da_uong_thuoc(self, thuoc):
        ngay_hien_tai = datetime.datetime.now().date().strftime("%Y-%m-%d")
        khoa_uong = f"{ngay_hien_tai}_{thuoc['thoi_gian']}"
        if 'lich_su_uong' not in thuoc:
            thuoc['lich_su_uong'] = []
        if khoa_uong not in thuoc['lich_su_uong']:
            thuoc['lich_su_uong'].append(khoa_uong)
        thuoc['trang_thai'] = 'da_uong'
        self.luu_danh_sach_thuoc()
        self.cap_nhat_thong_ke()

        self.cap_nhat_danh_sach_thuoc()
        self.da_gui_email = False

    def danh_dau_khong_uong_thuoc(self, thuoc):
        thuoc['trang_thai'] = 'khong_uong'
        self.luu_danh_sach_thuoc()
        self.cap_nhat_thong_ke()
        self.cap_nhat_danh_sach_thuoc()

    def bat_dau_camera(self):
        """Khởi động camera"""
        self.bat_dau_camera_signal.emit()

        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise Exception("Không thể mở camera")

            # Thiết lập thông số camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 0)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            self.camera_dang_hoat_dong = True
            self.kiem_tra_chuyen_dong_tay()

        except Exception as e:
            logging.error(f"Lỗi khi khởi động camera: {str(e)}")
            self.camera_dang_hoat_dong = False
    def tay_gan_mieng(self, hand_landmarks, face_landmarks):
        """Kiểm tra xem tay có gần miệng hay không"""
        if face_landmarks is None:
            return False

        # Lấy các điểm trên miệng
        mouth_indices = [13, 14]  # Môi dưới
        mouth_coords = []
        for idx in mouth_indices:
            mouth_landmark = face_landmarks.landmark[idx]
            mouth_coords.append((mouth_landmark.x, mouth_landmark.y))

        # Tính vị trí trung bình của miệng
        mouth_x = sum([coord[0] for coord in mouth_coords]) / len(mouth_coords)
        mouth_y = sum([coord[1] for coord in mouth_coords]) / len(mouth_coords)

        # Lấy vị trí đầu ngón tay (ví dụ: đầu ngón trỏ - điểm 8)
        hand_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        hand_x, hand_y = hand_tip.x, hand_tip.y

        # Tính khoảng cách giữa đầu ngón tay và miệng
        distance = ((hand_x - mouth_x) ** 2 + (hand_y - mouth_y) ** 2) ** 0.5

        # Ngưỡng để xác định 'gần'
        threshold = 0.1  # Điều chỉnh nếu cần

        return distance < threshold

    def gui_email(self, tieu_de, noi_dung):
        """Gửi email thông báo"""
        msg = MIMEMultipart()
        msg['From'] = self.gmail_nguoi_gui
        msg['To'] = self.gmail_nguoi_nhan
        msg['Subject'] = tieu_de

        msg.attach(MIMEText(noi_dung, 'plain'))

        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.gmail_nguoi_gui, self.gmail_mat_khau)
                server.sendmail(self.gmail_nguoi_gui, self.gmail_nguoi_nhan, msg.as_string())
            print("Đã gửi email thành công.")
        except Exception as e:
            print(f"Lỗi khi gửi email: {str(e)}")

    def kiem_tra_chuyen_dong_tay(self):
        """Xử lý frame từ camera và phát hiện chuyển động tay"""
        if not self.camera_dang_hoat_dong or self.cap is None:
            return

        try:
            ret, frame = self.cap.read()
            if not ret:
                raise Exception("Không thể đọc frame từ camera")

            # Xử lý frame
            frame = cv2.flip(frame, 1)  # Lật ngang để dễ nhìn hơn
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Phát hiện tay và khuôn mặt
            ket_qua_tay = self.hands.process(rgb_frame)
            ket_qua_khuon_mat = self.face_mesh.process(rgb_frame)

            # Khởi tạo các biến văn bản hiển thị
            van_ban1 = ""
            van_ban2 = ""
            van_ban3 = ""
            tay_gan_mieng_hien_tai = False

            # Xử lý phát hiện khuôn mặt
            face_landmarks = None
            if ket_qua_khuon_mat.multi_face_landmarks:
                self.phat_hien_khuon_mat = True
                if not self.thoi_gian_bat_dau_phat_hien_khuon_mat:
                    self.thoi_gian_bat_dau_phat_hien_khuon_mat = time.time()
                    logging.info("Bắt đầu phát hiện khuôn mặt")
                face_landmarks = ket_qua_khuon_mat.multi_face_landmarks[0]

                # Vẽ khung khuôn mặt
                for face_landmark in ket_qua_khuon_mat.multi_face_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame,
                        face_landmark,
                        self.mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing.DrawingSpec(
                            color=(0, 255, 0),
                            thickness=1,
                            circle_radius=1
                        )
                    )
            else:
                self.phat_hien_khuon_mat = False
                logging.debug("Không phát hiện khuôn mặt")

            # Xử lý phát hiện tay
            if ket_qua_tay.multi_hand_landmarks:
                for hand_landmarks in ket_qua_tay.multi_hand_landmarks:
                    # Vẽ các điểm mốc trên tay
                    self.mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(121, 22, 76), thickness=2, circle_radius=4),
                        self.mp_drawing.DrawingSpec(color=(250, 44, 250), thickness=2, circle_radius=2)
                    )

                    # Kiểm tra tay có gần miệng không
                    if self.tay_gan_mieng(hand_landmarks, face_landmarks):
                        tay_gan_mieng_hien_tai = True
                        if not self.tay_gan_mieng_truoc and tay_gan_mieng_hien_tai:
                            self.dem_tay += 1
                            logging.info(f"Phát hiện tay gần miệng lần {self.dem_tay}")

                        van_ban1 = f"Đưa tay lên miệng: {self.dem_tay}/2"
                        van_ban2 = "Bạn uống thuốc chưa hợp lệ"

                        if self.dem_tay >= 2:
                            try:
                                van_ban3 = "Đã uống thuốc thành công!"
                                logging.info("Đã xác nhận uống thuốc thành công")

                                # Đánh dấu đã uống thuốc
                                if hasattr(self, 'thuoc_hien_tai') and self.thuoc_hien_tai is not None:
                                    self.danh_dau_da_uong_thuoc(self.thuoc_hien_tai)
                                    logging.info(f"Đã đánh dấu thuốc {self.thuoc_hien_tai['ten']} là đã uống")

                                    # Thông báo bằng giọng nói
                                    threading.Thread(
                                        target=self.noi_tieng_viet,
                                        args=("Xác nhận uống thuốc thành công",),
                                        daemon=True
                                    ).start()

                                # Dừng camera sau 500ms
                                QTimer.singleShot(500, self.dung_camera)
                                return

                            except Exception as e:
                                logging.error(f"Lỗi khi xử lý hoàn thành uống thuốc: {str(e)}")
                                self.dung_camera()
                                return

            # Cập nhật trạng thái tay
            self.tay_gan_mieng_truoc = tay_gan_mieng_hien_tai

            # Vẽ vùng phát hiện miệng
            height, width = frame.shape[:2]
            mouth_area_height = int(0.3 * height)
            cv2.rectangle(frame, (0, 0), (width, mouth_area_height), (0, 255, 0), 2)

            # Chuyển đổi frame để vẽ text
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            draw = ImageDraw.Draw(pil_image)

            # Thiết lập font chữ
            font_path = 'C:\\Windows\\Fonts\\Arial.ttf'
            font_size = 24
            try:
                font = ImageFont.truetype(font_path, font_size)
            except IOError:
                logging.warning("Không tìm thấy font Arial, sử dụng font mặc định")
                font = ImageFont.load_default()

            # Vẽ văn bản
            if van_ban1:
                draw.text((10, 30), van_ban1, font=font, fill=(0, 255, 0))
            if van_ban2:
                draw.text((10, height - 50), van_ban2, font=font, fill=(255, 255, 255))
            if van_ban3:
                draw.text((10, 70), van_ban3, font=font, fill=(0, 255, 0))

            draw.text((10, mouth_area_height - 30), "Vùng phát hiện miệng", font=font, fill=(0, 255, 0))

            # Chuyển đổi lại frame và hiển thị
            frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            cv2.imshow('Camera Theo dõi', frame)

            # Kiểm tra phím thoát và lập lịch frame tiếp theo
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logging.info("Người dùng đã nhấn Q để dừng camera")
                self.dung_camera()
            elif self.camera_dang_hoat_dong:
                QTimer.singleShot(10, self.kiem_tra_chuyen_dong_tay)
            else:
                cv2.destroyAllWindows()

        except Exception as e:
            logging.error(f"Lỗi trong quá trình xử lý frame: {str(e)}")
            self.dung_camera()
    # In uongthuoc.py - Update UngDungNhacNhoUongThuocHienDai class

    def dung_camera(self):
        """Dừng và giải phóng tài nguyên camera"""
        try:
            self.camera_dang_hoat_dong = False

            if self.cap is not None:
                self.cap.release()
                self.cap = None

            cv2.destroyAllWindows()

            # Reset các biến trạng thái
            self.dem_tay = 0
            self.thoi_gian_tay_cuoi = 0
            self.tay_gan_mieng_truoc = False
            self.thoi_gian_bat_dau_phat_hien_khuon_mat = None
            self.che_do_canh_bao = False
            self.phat_hien_khuon_mat = False
            self.da_gui_email = False

            self.dung_camera_signal.emit()

        except Exception as e:
            logging.error(f"Lỗi khi dừng camera: {str(e)}")
    def cleanup_final(self):
        """Cleanup cuối cùng sau khi dừng camera"""
        try:
            if hasattr(self, 'hands'):
                self.hands.close()
            if hasattr(self, 'face_mesh'):
                self.face_mesh.close()

            # Cập nhật UI
            self.cap_nhat_danh_sach_thuoc()
            self.cap_nhat_thong_ke()
            logging.info("Hoàn tất quy trình dừng camera và cleanup")
        except Exception as e:
            logging.error(f"Lỗi trong cleanup_final: {str(e)}")

    def reset_danh_sach_thuoc_da_nhac(self):
        """Reset danh sách thuốc đã nhắc vào lúc nửa đêm mỗi ngày."""
        while True:
            now = datetime.datetime.now()
            next_day = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_day - now).total_seconds()
            time.sleep(sleep_seconds)
            self.danh_sach_thuoc_da_nhac = []

    def bat_dau_luong_reset_hang_ngay(self):
        """Bắt đầu luồng reset danh sách thuốc đã nhắc hàng ngày."""
        luong_reset = threading.Thread(target=self.reset_danh_sach_thuoc_da_nhac)
        luong_reset.daemon = True
        luong_reset.start()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Đặt kiểu ứng dụng
    app.setStyle('Fusion')

    # Đặt font cho tiếng Việt
    font = QFont("Arial", 10)
    app.setFont(font)

    # Đặt giao diện
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#F5F6FA"))
    palette.setColor(QPalette.WindowText, QColor("#2C3E50"))
    palette.setColor(QPalette.Base, QColor("white"))
    palette.setColor(QPalette.AlternateBase, QColor("#F5F6FA"))
    palette.setColor(QPalette.Text, QColor("#2C3E50"))
    palette.setColor(QPalette.Button, QColor("white"))
    palette.setColor(QPalette.ButtonText, QColor("#2C3E50"))
    app.setPalette(palette)

    cua_so = UngDungNhacNhoUongThuocHienDai()
    cua_so.show()

    sys.exit(app.exec_())