from odoo import http, fields
from odoo.http import request
from datetime import datetime


class MobileSyncDemo(http.Controller):
    """
    return records from school changed/created since 'since'.
    since: ISO UTC o None para full (ej. 2025-09-08T00:00:00)
    limit: basic pagination include_inactive: if True no filter active
    """

    @http.route('/api/v1/student', type='json', auth='user', methods=['POST'], csrf=False)
    def school_delta(self, since=None, limit=200, include_inactive=False):

        domain = []
        if not include_inactive:
            domain.append(('active', '=', True))

        # Manejo de parámetro 'since'
        if since:
            try:
                # Convertir string ISO a datetime usando Odoo utils
                since_dt = fields.Datetime.from_string(since)
                domain.extend([
                    '|',
                    ('create_date', '>', since_dt),
                    ('write_date', '>', since_dt)
                ])
            except Exception:
                return {"error": "Formato inválido en parámetro 'since'. Use ISO UTC ej: 2025-09-08T00:00:00"}

        # Paginación segura
        try:
            limit = int(limit or 200)
        except ValueError:
            limit = 200

        students = (
            request.env['school.student']
            .with_context(prefetch_fields=False)
            .search(domain, order='write_date,id', limit=limit)
        )

        fields_to_read = [
            'id', 'active', 'write_date',
            'credential_number', 'name',
            'cellphone', 'grade_level', 'group'
        ]

        items = students.read(fields_to_read)

        return {
            "items": items,
            "server_time": datetime.utcnow().isoformat(timespec="seconds") + 'Z',
        }
