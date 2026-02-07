import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Layout } from './Layout';

describe('Layout', () => {
  beforeEach(() => {
    // Reset matchMedia mock before each test
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('should render avatar and text areas', () => {
    render(
      <Layout
        avatarArea={<div data-testid="avatar">Avatar</div>}
        textArea={<div data-testid="text">Text</div>}
      />
    );

    expect(screen.getByTestId('avatar')).toBeInTheDocument();
    expect(screen.getByTestId('text')).toBeInTheDocument();
  });

  it('should apply desktop class when screen is wide', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    const { container } = render(
      <Layout
        avatarArea={<div>Avatar</div>}
        textArea={<div>Text</div>}
      />
    );

    expect(container.firstChild).toHaveClass('desktop');
  });

  it('should apply mobile class when screen is narrow', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    const { container } = render(
      <Layout
        avatarArea={<div>Avatar</div>}
        textArea={<div>Text</div>}
      />
    );

    expect(container.firstChild).toHaveClass('mobile');
  });

  it('should have avatar-section and text-section classes', () => {
    const { container } = render(
      <Layout
        avatarArea={<div>Avatar</div>}
        textArea={<div>Text</div>}
      />
    );

    expect(container.querySelector('.avatar-section')).toBeInTheDocument();
    expect(container.querySelector('.text-section')).toBeInTheDocument();
  });
});
