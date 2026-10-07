import random
import sys
import os
import threading
import time
import logging
from collections import deque
from datetime import datetime, timedelta
from queue import Queue
import cv2

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QMessageBox, QScrollArea, QHBoxLayout, QStackedWidget, QFrame, QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QTime
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
import numpy as np

from gtts import gTTS
import pygame
import tempfile
import json
import traceback

# Import các module con
from vanthaodong import PhanBaiTapVanDong

# Khởi tạo logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


class FakeTimeManager:
    """Quản lý thời gian giả (faketime) cho ứng dụng"""

    def __init__(self, time_multiplier=10, start_hour=1):
        """
        time_multiplier: Số phút faketime tương ứng 1 giây thực
        start_hour: Giờ bắt đầu (faketime)
        """
        self.time_multiplier = time_multiplier  # 1 giây thực = 10 phút giả
        self.start_time = datetime.now()

        # Thiết lập giờ bắt đầu faketime
        self.fake_start_time = datetime.now().replace(
            hour=start_hour,
            minute=12,
            second=0,
            microsecond=0
        )

        # Timer để cập nhật UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.notify_time_update)
        self.update_timer.start(1000)  # Cập nhật mỗi giây

        # Callback khi thời gian thay đổi
        self.time_updated_callbacks = []

    def get_fake_time(self) -> datetime:
        """Lấy thời gian giả hiện tại, với phút luôn là bội số của 10"""
        elapsed_seconds = (datetime.now() - self.start_time).total_seconds()
        fake_elapsed_minutes = elapsed_seconds * self.time_multiplier

        # Tính thời gian giả
        fake_time = self.fake_start_time + timedelta(minutes=fake_elapsed_minutes)

        # Làm tròn phút xuống bội số của 10 gần nhất
        minute = (fake_time.minute // 10) * 10

        # Tạo datetime mới với phút đã làm tròn và luôn đặt giây là 0
        rounded_fake_time = fake_time.replace(minute=minute, second=0, microsecond=0)

        return rounded_fake_time

    def get_fake_time_str(self, format_str="%H:%M:%S") -> str:
        """Lấy thời gian giả dưới dạng chuỗi định dạng"""
        fake_time = self.get_fake_time()
        return fake_time.strftime(format_str)

    def register_time_updated_callback(self, callback):
        """Đăng ký callback khi thời gian thay đổi"""
        if callback not in self.time_updated_callbacks:
            self.time_updated_callbacks.append(callback)

    def notify_time_update(self):
        """Thông báo cho các callback khi thời gian thay đổi"""
        current_time = self.get_fake_time()
        for callback in self.time_updated_callbacks:
            try:
                callback(current_time)
            except Exception as e:
                logging.error(f"Lỗi trong callback thời gian: {e}")


class QuanLyCamera:
    def __init__(self):
        self.mayAnh = None
        self.khoa = threading.Lock()
        self.hangDoiKhungHinh = Queue(maxsize=1)
        self.dangChay = False
        self.luongMayAnh = None

    def khoiTaoCamera(self):
        """Khởi tạo camera ban đầu"""
        try:
            self.mayAnh = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            time.sleep(1)  # Đợi camera khởi động

            if not self.mayAnh.isOpened():
                raise Exception("Không thể mở camera")

            # Thiết lập thông số camera với độ phân giải cao hơn
            self.mayAnh.set(cv2.CAP_PROP_FRAME_WIDTH, 1980)
            self.mayAnh.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.mayAnh.set(cv2.CAP_PROP_FPS, 30)

            # Thêm thiết lập để cải thiện chất lượng hình ảnh
            self.mayAnh.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Bật tự động lấy nét
            self.mayAnh.set(cv2.CAP_PROP_BRIGHTNESS, 128)  # Độ sáng trung bình
            self.mayAnh.set(cv2.CAP_PROP_CONTRAST, 128)  # Độ tương phản trung bình

            # Đọc thử frame đầu tiên
            ret, _ = self.mayAnh.read()
            if not ret:
                raise Exception("Không đọc được frame từ camera")

            logging.info("Khởi tạo camera thành công")
            return True

        except Exception as e:
            logging.error(f"Lỗi khởi tạo camera: {str(e)}")
            if self.mayAnh is not None:
                self.mayAnh.release()
                self.mayAnh = None
            return False

    def batDauCatHinh(self):
        """Bắt đầu luồng đọc frame từ camera"""
        if self.dangChay:
            return

        if self.mayAnh is None and not self.khoiTaoCamera():
            return

        self.dangChay = True
        self.luongMayAnh = threading.Thread(target=self._docKhungHinh)
        self.luongMayAnh.daemon = True
        self.luongMayAnh.start()
        logging.info("Bắt đầu đọc frame từ camera")

    def _docKhungHinh(self):
        """Luồng chạy nền đọc frames từ camera"""
        while self.dangChay and self.mayAnh is not None:
            try:
                ret, khungHinh = self.mayAnh.read()
                if ret:
                    # Khung hình đã có kích thước 640x480 từ camera, không cần resize
                    if not self.hangDoiKhungHinh.full():
                        self.hangDoiKhungHinh.put(khungHinh)
                    else:
                        # Nếu hàng đợi đầy, lấy ra một khung hình cũ và thêm frame mới
                        try:
                            self.hangDoiKhungHinh.get_nowait()
                            self.hangDoiKhungHinh.put(khungHinh)
                        except:
                            pass
                else:
                    # Nếu đọc camera lỗi, thử khởi tạo lại
                    logging.error("Lỗi đọc frame từ camera, thử khởi tạo lại")
                    if self.mayAnh is not None:
                        self.mayAnh.release()
                        self.mayAnh = None

                    # Thử khởi tạo lại camera sau 1 giây
                    time.sleep(1)
                    self.mayAnh = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    if not self.mayAnh.isOpened():
                        logging.error("Không thể khởi tạo lại camera")
                        break

                # Giảm thời gian sleep để tăng tần suất cập nhật
                time.sleep(0.03)  # 30ms

            except Exception as e:
                logging.error(f"Lỗi trong quá trình đọc frame: {str(e)}")
                time.sleep(0.5)  # Đợi lâu hơn nếu có lỗi
                continue

        self.dungCatHinh()

    def layKhungHinh(self):
        """Lấy frame từ queue"""
        if not self.hangDoiKhungHinh.empty():
            return self.hangDoiKhungHinh.get()
        return None

    def dungCatHinh(self):
        with self.khoa:
            self.dangChay = False
            if self.luongMayAnh and self.luongMayAnh != threading.current_thread():
                try:
                    self.luongMayAnh.join(timeout=1.0)
                except RuntimeError:
                    pass  # Bỏ qua lỗi nếu là thread hiện tại

            if self.mayAnh:
                self.mayAnh.release()
                self.mayAnh = None

            while not self.hangDoiKhungHinh.empty():
                self.hangDoiKhungHinh.get()

            logging.info("Đã dừng đọc frame và giải phóng camera")


class LuongXuLy(QThread):
    khungHinhDaXuLy = pyqtSignal(object)

    def __init__(self, quanLyCamera):
        super().__init__()
        self.quanLyCamera = quanLyCamera
        self.dangChay = False

    def run(self):
        self.dangChay = True
        while self.dangChay:
            khungHinh = self.quanLyCamera.layKhungHinh()
            if khungHinh is not None:
                self.khungHinhDaXuLy.emit(khungHinh)
            time.sleep(0.03)

    def dung(self):
        self.dangChay = False
        self.wait()


class HeThongChamSoc(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🩺 Hệ Thống Chăm Sóc Sức Khỏe")
        self.setGeometry(100, 100, 1600, 900)
        self.setWindowIcon(QIcon("icons/app_icon.png"))

        # Khởi tạo FakeTimeManager (1 giây thực = 10 phút fake, bắt đầu từ 1:12)
        self.fake_time_manager = FakeTimeManager(time_multiplier=10, start_hour=1)

        # Thời gian bắt đầu (dùng làm mốc tính)
        self.thoiGianBatDau = datetime.now()

        # Khởi tạo quản lý camera
        self.quanLyCamera = QuanLyCamera()

        # Khởi tạo luồng xử lý chính
        self.luongXuLy = LuongXuLy(self.quanLyCamera)
        self.luongXuLy.khungHinhDaXuLy.connect(self.khiKhungHinhDaXuLy)

        # Khởi tạo pygame mixer cho phát âm thanh
        pygame.mixer.init()

        # Thêm biến theo dõi báo cáo đã gửi
        self.da_gui_bao_cao_hom_nay = False
        self.ngay_hien_tai = None

        # Đăng ký callback cập nhật thời gian
        self.fake_time_manager.register_time_updated_callback(self.update_fake_time_display)
        # Đăng ký callback kiểm tra gửi báo cáo
        self.fake_time_manager.register_time_updated_callback(self.kiem_tra_gui_bao_cao)

        # Gọi các phương thức khởi tạo sau
        self.khoiTaoModules()
        self.khoiTaoGiaoDien()

        # Bắt đầu camera và xử lý
        self.quanLyCamera.batDauCatHinh()
        self.luongXuLy.start()

    def khoiTaoModules(self):
        """
        Khởi tạo các module cho ứng dụng
        """
        try:
            # Module xử lý ảnh
            from xulyanh import MainWindow as XuLyAnhWindow
            self.xuLyAnh = XuLyAnhWindow()
            self.xuLyAnh.setWindowFlags(Qt.Widget)

            # Khởi tạo biến đếm frame để kiểm soát tần suất xử lý
            self.frame_process_counter = 0

            # ===== MODULE VẬN ĐỘNG =====
            # Tạo container chính cho module vận động
            self.vanDong = QWidget()
            self.vanDong.setStyleSheet("background-color: #ffffff;")

            # Layout chính là VBoxLayout (từ trên xuống)
            mainVanDongLayout = QVBoxLayout(self.vanDong)
            mainVanDongLayout.setContentsMargins(20, 20, 20, 20)
            mainVanDongLayout.setSpacing(0)

            # Khởi tạo bài tập vận động từ module vanthaodong
            self.baiTap = PhanBaiTapVanDong(self)

            # Thêm bài tập vào layout
            mainVanDongLayout.addWidget(self.baiTap, 1)

            # ===== CÁC MODULE KHÁC =====
            # Module uống thuốc
            from uongthuoc import UngDungNhacNhoUongThuocHienDai
            self.uongThuoc = UngDungNhacNhoUongThuocHienDai()
            self.uongThuoc.setWindowFlags(Qt.Widget)

            # Module tâm lý
            from phan_tich_tam_ly import GiaoDienKhaoSat
            self.tamLy = GiaoDienKhaoSat()
            self.tamLy.setWindowFlags(Qt.Widget)

            # Kết nối signals từ module bài tập vận động
            self.baiTap.bat_dau_bai_tap_signal.connect(self.khiBatDauTapTheDuc)
            self.baiTap.ket_thuc_bai_tap_signal.connect(self.khiKetThucTapTheDuc)
            self.uongThuoc.bat_dau_camera_signal.connect(self.khiBatDauUongThuoc)
            self.uongThuoc.dung_camera_signal.connect(self.khiKetThucUongThuoc)

            logging.info("Khởi tạo các module thành công")
        except Exception as e:
            logging.error(f"Lỗi khởi tạo module: {str(e)}")
            traceback.print_exc()
            raise

    def khoiTaoGiaoDien(self):
        try:
            # Thiết lập widget chính
            centralWidget = QWidget()
            self.setCentralWidget(centralWidget)
            mainLayout = QHBoxLayout(centralWidget)
            mainLayout.setContentsMargins(0, 0, 0, 0)
            mainLayout.setSpacing(0)

            # Thanh điều hướng bên trái
            thanhDinhHuong = QFrame()
            thanhDinhHuong.setFixedWidth(180)
            thanhDinhHuong.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    border-right: 1px solid #e0e0e0;
                }
                QPushButton {
                    background-color: #f8f8f8;
                    color: #333333;
                    border: none;
                    padding: 12px 8px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 0px;
                    margin: 1px 0px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:checked {
                    background-color: #2196F3;
                    color: white;
                }
            """)
            layoutThanhDinhHuong = QVBoxLayout(thanhDinhHuong)
            layoutThanhDinhHuong.setContentsMargins(0, 0, 0, 0)
            layoutThanhDinhHuong.setSpacing(0)

            # Logo ứng dụng
            logo = QLabel()
            pixmap = QPixmap("icons/logo.png")
            if not pixmap.isNull():
                logo.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo.setAlignment(Qt.AlignCenter)
                logo.setStyleSheet("margin: 10px 0;")
            else:
                logo = QLabel("HỆ THỐNG")
                logo.setStyleSheet("""
                    color: #333333;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                    text-align: center;
                """)
                logo.setAlignment(Qt.AlignCenter)
            layoutThanhDinhHuong.addWidget(logo)

            # Các nút điều hướng
            self.btnTheoDoiSucKhoe = QPushButton("🖥️ Theo dõi")
            self.btnTheoDoiSucKhoe.setCheckable(True)
            self.btnTheoDoiSucKhoe.setChecked(True)
            self.btnTheoDoiSucKhoe.clicked.connect(lambda: self.chuyenModule(0))

            self.btnVanDong = QPushButton("🏋️‍♂️ Vận động")
            self.btnVanDong.setCheckable(True)
            self.btnVanDong.clicked.connect(lambda: self.chuyenModule(1))

            self.btnUongThuoc = QPushButton("💊 Uống thuốc")
            self.btnUongThuoc.setCheckable(True)
            self.btnUongThuoc.clicked.connect(lambda: self.chuyenModule(2))

            self.btnTamLy = QPushButton("🧘‍♀️ Tâm lý")
            self.btnTamLy.setCheckable(True)
            self.btnTamLy.clicked.connect(lambda: self.chuyenModule(3))

            # Cập nhật mảng nhóm nút
            self.nhomNut = [self.btnTheoDoiSucKhoe, self.btnVanDong, self.btnUongThuoc, self.btnTamLy]
            for nut in self.nhomNut:
                layoutThanhDinhHuong.addWidget(nut)

            layoutThanhDinhHuong.addStretch()

            # Thông tin phiên bản
            phienBan = QLabel("Phiên bản 1.0")
            phienBan.setStyleSheet("""
                color: #555555;
                font-size: 10px;
                padding: 5px;
                text-align: center;
            """)
            phienBan.setAlignment(Qt.AlignCenter)
            layoutThanhDinhHuong.addWidget(phienBan)

            # Khu vực nội dung chính - StackedWidget
            self.stack = QStackedWidget()
            self.stack.setStyleSheet("""
                QStackedWidget {
                    background-color: #ffffff;
                }
            """)

            # Thêm các module vào stack
            self.stack.addWidget(self.xuLyAnh)
            self.stack.addWidget(self.vanDong)
            self.stack.addWidget(self.uongThuoc)
            self.stack.addWidget(self.tamLy)

            # Thêm các widget vào layout chính
            mainLayout.addWidget(thanhDinhHuong)
            mainLayout.addWidget(self.stack, 5)

            # Thanh trạng thái
            thanhTrangThai = self.statusBar()
            thanhTrangThai.setStyleSheet("""
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #333333;
                    font-size: 12px;
                    padding: 3px;
                    border-top: 1px solid #e0e0e0;
                }
            """)
            thanhTrangThai.showMessage("Đang kết nối camera...")

            # Nhãn hiển thị thời gian
            labelThoiGian = QLabel()
            labelThoiGian.setAlignment(Qt.AlignCenter)
            labelThoiGian.setFont(QFont("Segoe UI", 14, QFont.Bold))
            labelThoiGian.setStyleSheet("""
                QLabel {
                    color: #333333;
                    padding: 5px;
                    margin-right: 10px;
                }
            """)
            thanhTrangThai.addPermanentWidget(labelThoiGian)
            self.labelThoiGian = labelThoiGian

            # Timer cập nhật thời gian - BỎ TIMER CŨ VÌ ĐÃ CÓ FAKE TIME MANAGER
            # timerCapNhat = QTimer()
            # timerCapNhat.timeout.connect(self.capNhatThoiGian)
            # timerCapNhat.start(1000)
            # self.timerCapNhat = timerCapNhat

            # Cập nhật style toàn cục
            self.setStyleSheet("""
                QWidget {
                    font-family: 'Segoe UI', 'Arial Unicode MS', Tahoma, sans-serif;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #f0f0f0;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #c0c0c0;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: #f0f0f0;
                    height: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:horizontal {
                    background: #c0c0c0;
                    min-width: 20px;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    height: 0px;
                    width: 0px;
                }
            """)

            # Thiết lập độ ưu tiên luồng để giảm lag
            if hasattr(self, 'luongXuLy'):
                self.luongXuLy.setPriority(QThread.NormalPriority)

            # Tối đa hóa cửa sổ để có nhiều không gian nhất có thể
            self.setWindowState(Qt.WindowMaximized)

            logging.info("Khởi tạo giao diện thành công")
        except Exception as e:
            logging.error(f"Lỗi khởi tạo giao diện: {str(e)}")
            QMessageBox.critical(self, "Lỗi", f"Không thể khởi tạo giao diện: {str(e)}")

    def chuyenModule(self, index):
        self.stack.setCurrentIndex(index)
        for i, nut in enumerate(self.nhomNut):
            nut.setChecked(i == index)

    def khiKhungHinhDaXuLy(self, khungHinh):
        try:
            if not isinstance(khungHinh, np.ndarray):
                return

            # Chỉ truyền khung hình khi đang ở tab xử lý ảnh
            if self.stack.currentIndex() == 0 and hasattr(self, 'xuLyAnh'):
                # Thêm cơ chế giảm tần suất xử lý frame để giảm tải CPU
                self.frame_process_counter += 1
                if self.frame_process_counter % 3 != 0:  # Tối ưu: Chỉ xử lý 1 frame trong mỗi 3 frame
                    return

                # Giảm kích thước khung hình để cải thiện hiệu suất
                khungHinh = cv2.resize(khungHinh, (720, 480))

                # Xử lý frame
                processed_frame = self.xuLyAnh.xu_ly_frame(khungHinh)

                # Cập nhật thanh trạng thái không quá thường xuyên
                if not hasattr(self, 'last_status_update'):
                    self.last_status_update = 0

                current_time = time.time()
                if current_time - self.last_status_update >= 1.0:  # Cập nhật mỗi giây
                    self.last_status_update = current_time
                    self.statusBar().showMessage("Đang xử lý camera")

        except Exception as e:
            logging.error(f"Lỗi xử lý frame: {str(e)}")
            if hasattr(self, 'exception_count'):
                self.exception_count += 1
            else:
                self.exception_count = 1

            # Chỉ hiển thị thông báo lỗi mỗi 10 lần để tránh lag
            if self.exception_count % 10 == 1:
                self.statusBar().showMessage(f"Lỗi xử lý camera: {str(e)}")

    def update_fake_time_display(self, fake_time):
        """Cập nhật hiển thị thời gian giả - CHỈ DÙNG HÀM NÀY"""
        time_str = fake_time.strftime("%H:%M:%S")
        date_str = fake_time.strftime("%d/%m/%Y")
        self.labelThoiGian.setText(f"🕒 {time_str} {date_str}")

    def kiem_tra_gui_bao_cao(self, fake_time):
        """Kiểm tra và gửi báo cáo vận động vào 23:00 mỗi ngày"""
        try:
            ngay_hien_tai = fake_time.date()
            gio_hien_tai = fake_time.time()

            # Reset flag khi chuyển ngày mới
            if self.ngay_hien_tai != ngay_hien_tai:
                self.da_gui_bao_cao_hom_nay = False
                self.ngay_hien_tai = ngay_hien_tai

            # Gửi báo cáo vào 23:00 và chưa gửi hôm nay
            if gio_hien_tai.hour == 20 and gio_hien_tai.minute == 0 and not self.da_gui_bao_cao_hom_nay:
                self.gui_bao_cao_van_dong()
                self.da_gui_bao_cao_hom_nay = True

        except Exception as e:
            logging.error(f"Lỗi kiểm tra gửi báo cáo: {e}")

    def gui_bao_cao_van_dong(self):
        """Gửi báo cáo vận động cuối ngày"""
        try:
            # Import ở đây để tránh circular import
            from vanthaodong import BaoCaoSucKhoe

            # Lấy thông tin bài tập từ module vận động
            tan_suat = self.baiTap.thong_ke_bai_tap()

            # Tạo và gửi báo cáo
            bao_cao = BaoCaoSucKhoe()
            noi_dung = bao_cao.tao_bao_cao_bai_tap(tan_suat)


            # Gửi email (sử dụng email từ vanthaodong.py)
            email_nguoi_nhan = 'maianhquan317@gmail.com'  # Hoặc lấy từ config
            ket_qua = bao_cao.gui_bao_cao(email_nguoi_nhan, noi_dung)

            if ket_qua:
                logging.info("Đã gửi báo cáo vận động cuối ngày thành công.")
                self.statusBar().showMessage("Đã gửi báo cáo vận động qua email", 5000)
            else:
                logging.error("Gửi báo cáo vận động thất bại.")
                self.statusBar().showMessage("Lỗi gửi báo cáo vận động", 5000)

        except Exception as e:
            logging.error(f"Lỗi gửi báo cáo vận động: {e}")
            self.statusBar().showMessage(f"Lỗi gửi báo cáo: {str(e)}", 5000)

    def phat_am_thanh(self, text):
        """Phát âm thanh thông báo bằng gTTS"""
        try:
            # Không gọi pygame.mixer.init() nếu đã được khởi tạo
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            tts = gTTS(text=text, lang='vi')
            tts.save("thongbao.mp3")
            pygame.mixer.music.load("thongbao.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()

            # Xóa file tạm nhưng KHÔNG quit mixer để các module khác vẫn sử dụng được
            try:
                os.remove("thongbao.mp3")
            except:
                pass  # Bỏ qua lỗi nếu không xóa được file

        except Exception as e:
            logging.error(f"Lỗi phát âm thanh: {str(e)}")

    def khiBatDauTapTheDuc(self):
        self.luongXuLy.dung()
        self.quanLyCamera.dungCatHinh()
        self.statusBar().showMessage("Đã chuyển camera cho module vận động")
        logging.info("Đã chuyển camera cho module vận động")

    def khiKetThucTapTheDuc(self):
        self.quanLyCamera.batDauCatHinh()
        self.luongXuLy.start()
        self.statusBar().showMessage("Đã khôi phục camera xử lý ảnh")
        logging.info("Đã khôi phục camera xử lý ảnh")

    def khiBatDauUongThuoc(self):
        self.luongXuLy.dung()
        self.quanLyCamera.dungCatHinh()
        self.statusBar().showMessage("Đã chuyển camera cho module uống thuốc")
        logging.info("Đã chuyển camera cho module uống thuốc")

    def khiKetThucUongThuoc(self):
        self.quanLyCamera.batDauCatHinh()
        self.luongXuLy.start()
        self.statusBar().showMessage("Đã khôi phục camera xử lý ảnh")
        logging.info("Đã khôi phục camera xử lý ảnh")

    def closeEvent(self, event):
        """Xử lý khi đóng chương trình"""
        try:
            # Dừng các luồng xử lý
            self.luongXuLy.dung()
            self.quanLyCamera.dungCatHinh()

            # Dừng fake time manager
            if hasattr(self, 'fake_time_manager'):
                self.fake_time_manager.update_timer.stop()

            # Dọn dẹp pygame mixer - CHỈ KHI ĐÓNG ỨNG DỤNG
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
            except:
                pass

            logging.info("Đóng chương trình")
            event.accept()
        except Exception as e:
            logging.error(f"Lỗi khi đóng chương trình: {e}")
            event.accept()


def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        cuaSo = HeThongChamSoc()
        cuaSo.app = app  # Lưu tham chiếu đến app
        cuaSo.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"Lỗi khởi động: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()