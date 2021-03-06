##############################################################################
#
#    Copyright (C) 20121 :) joannes.landy@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Market base",
    "category" : "Market",
    "version" : "1.0",
    "depends" : ["base"],
    "author" : "joannes.landy@gmail.com",
    "description": """
    Market exchange base module
    """,
    'init_xml': [],
    'data': [
        "security/ir.model.access.csv",
        "views/market_menu.xml",
        "views/market_exchange_view.xml",
        "views/res_config_settings_views.xml",




    ],
    'demo_xml': [],
    'installable': True,
}

