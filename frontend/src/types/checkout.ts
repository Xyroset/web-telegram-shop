import type { OrderCreateRequestRequest } from '@/api/models/OrderCreateRequestRequest';
import type { CreateInvoiceRequestRequest } from '@/api/models/CreateInvoiceRequestRequest';

export type CreateOrderCommand = OrderCreateRequestRequest;
export type CreateTransactionCommand = CreateInvoiceRequestRequest;
