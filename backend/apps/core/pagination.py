from rest_framework.pagination import CursorPagination, LimitOffsetPagination


class ProductListPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 50


class ReviewListPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "c"


class OrderListPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "c"


class TransactionListPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "c"
