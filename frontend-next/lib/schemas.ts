import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});
export type LoginForm = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    username: z.string().min(2, 'Username is required'),
    first_name: z.string().min(1, 'First name is required'),
    last_name: z.string().optional(),
    password: z
      .string()
      .min(8, 'At least 8 characters')
      .regex(/[A-Z]/, 'Need an uppercase letter')
      .regex(/[0-9]/, 'Need a digit')
      .regex(/[!@#$%^&*]/, 'Need a special character'),
    password_confirm: z.string().min(1, 'Confirm your password'),
  })
  .refine((d) => d.password === d.password_confirm, {
    message: 'Passwords do not match',
    path: ['password_confirm'],
  });
export type RegisterForm = z.infer<typeof registerSchema>;

export const caseCreateSchema = z.object({
  case_number: z.string().min(1, 'Case number is required'),
  cnr_number: z.string().optional(),
  title: z.string().min(1, 'Title is required'),
  case_type: z.string().min(1, 'Case type is required'),
  priority: z.enum(['URGENT', 'HIGH', 'NORMAL', 'LOW']).default('NORMAL'),
  filing_date: z.string().min(1, 'Filing date is required'),
  plaintiff_name: z.string().optional(),
  defendant_name: z.string().optional(),
  description: z.string().optional(),
});
export type CaseCreateForm = z.input<typeof caseCreateSchema>;
