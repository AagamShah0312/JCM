import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge, Badge, EmptyState } from '@/components/ui';

describe('UI primitives (spec §51/§81)', () => {
  it('renders a status badge with the label', () => {
    render(<StatusBadge status="ACTIVE" />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders a fallback for unknown status', () => {
    render(<StatusBadge status="WEIRD" />);
    expect(screen.getByText('WEIRD')).toBeInTheDocument();
  });

  it('renders a badge tone', () => {
    render(<Badge tone="green">OK</Badge>);
    expect(screen.getByText('OK')).toBeInTheDocument();
  });

  it('renders an empty state with action', () => {
    render(<EmptyState title="Nothing here" message="Add something" action={<button>Add</button>} />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.getByText('Add')).toBeInTheDocument();
  });
});
