import { describe, it, expect } from 'vitest';
import { loginSchema, registerSchema, caseCreateSchema } from '@/lib/schemas';

describe('loginSchema (spec §53)', () => {
  it('accepts valid credentials', () => {
    expect(loginSchema.safeParse({ email: 'a@b.com', password: 'x' }).success).toBe(true);
  });

  it('rejects invalid email', () => {
    const r = loginSchema.safeParse({ email: 'not-an-email', password: 'x' });
    expect(r.success).toBe(false);
  });

  it('rejects empty password', () => {
    const r = loginSchema.safeParse({ email: 'a@b.com', password: '' });
    expect(r.success).toBe(false);
  });
});

describe('registerSchema (spec §53)', () => {
  const base = { username: 'user1', first_name: 'A', password: 'Passw0rd!', password_confirm: 'Passw0rd!' };

  it('accepts a strong password', () => {
    expect(registerSchema.safeParse(base).success).toBe(true);
  });

  it('rejects weak passwords', () => {
    for (const pwd of ['short', 'nouppercase1!', 'NODIGITS!', 'NoSpecial1']) {
      const r = registerSchema.safeParse({ ...base, password: pwd, password_confirm: pwd });
      expect(r.success).toBe(false);
    }
  });

  it('rejects mismatched confirmation', () => {
    const r = registerSchema.safeParse({ ...base, password_confirm: 'Different1!' });
    expect(r.success).toBe(false);
  });
});

describe('caseCreateSchema (spec §8/§53)', () => {
  const base = { case_number: 'C-1', title: 'Test Case', case_type: 'Civil', filing_date: '2026-01-01' };

  it('accepts a valid case', () => {
    expect(caseCreateSchema.safeParse(base).success).toBe(true);
  });

  it('defaults priority to NORMAL', () => {
    const r = caseCreateSchema.safeParse(base);
    expect(r.success && r.data.priority).toBe('NORMAL');
  });

  it('rejects missing title', () => {
    const r = caseCreateSchema.safeParse({ ...base, title: '' });
    expect(r.success).toBe(false);
  });
});
