# Copyright (c) 2025 Ricardo Espantaleón Pérez
# SPDX-License-Identifier: Apache-2.0

from enum import Enum


class TemplateEngine(str, Enum):
    JINJA2 = "jinja2"
    NUNJUCKS = "nunjucks"
