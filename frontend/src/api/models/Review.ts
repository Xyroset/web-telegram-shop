/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ReviewPhoto } from './ReviewPhoto';
export type Review = {
	readonly id: string;
	readonly user: Record<string, any>;
	readonly is_author: boolean;
	rating?: number;
	text?: string | null;
	readonly photos: Array<ReviewPhoto>;
	admin_reply_text?: string | null;
	readonly created_at: string;
	admin_reply_created_at?: string | null;
};
