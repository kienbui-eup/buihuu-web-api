#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2020-2024      David Straub
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#

"""Tên thương hiệu của bản triển khai này.

Bản gốc nhắc "Gramps Web" trong vài chuỗi gửi tới người dùng cuối (thư xác nhận
địa chỉ, thư đặt lại mật khẩu). Gom về một chỗ để đổi tên chỉ sửa một file.

Không dùng cho những chỗ nhắc tới phần mềm với tư cách phần mềm: tiêu đề OpenAPI
"Gramps Web API", chuỗi phiên bản, tên định dạng Gramps XML, hay dòng bản quyền.
Những chỗ đó phải giữ nguyên.
"""

APP_NAME = "Phả hệ Bùi Hữu"

# Ngôn ngữ mặc định khi lời gọi API không kèm tham số `locale`.
#
# Bản gốc lùi về GRAMPS_LOCALE, tức locale của tiến trình máy chủ - thường là
# tiếng Anh trong container. Trang này của một dòng họ Việt Nam nên phần chữ do
# máy chủ sinh ra (tên loại sự kiện, quan hệ họ hàng, chuỗi ngày tháng) mặc định
# phải là tiếng Việt.
DEFAULT_LANGUAGE = "vi"
