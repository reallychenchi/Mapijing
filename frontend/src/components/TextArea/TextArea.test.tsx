import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TextArea } from './TextArea';

describe('TextArea', () => {
  it('should render text content', () => {
    render(
      <TextArea
        text="Hello World"
        speaker="user"
        isStreaming={false}
      />
    );

    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('should apply user class for user speaker', () => {
    render(
      <TextArea
        text="User message"
        speaker="user"
        isStreaming={false}
      />
    );

    const textElement = screen.getByText('User message');
    expect(textElement).toHaveClass('user');
  });

  it('should apply assistant class for assistant speaker', () => {
    render(
      <TextArea
        text="Assistant message"
        speaker="assistant"
        isStreaming={false}
      />
    );

    const textElement = screen.getByText('Assistant message');
    expect(textElement).toHaveClass('assistant');
  });

  it('should show cursor when streaming', () => {
    render(
      <TextArea
        text="Streaming text"
        speaker="assistant"
        isStreaming={true}
      />
    );

    expect(screen.getByText('|')).toBeInTheDocument();
  });

  it('should not show cursor when not streaming', () => {
    render(
      <TextArea
        text="Static text"
        speaker="assistant"
        isStreaming={false}
      />
    );

    expect(screen.queryByText('|')).not.toBeInTheDocument();
  });

  it('should render error display when error is provided', () => {
    const onRetry = vi.fn();

    render(
      <TextArea
        text="Some text"
        speaker="assistant"
        isStreaming={false}
        error={{
          message: '网络错误',
          onRetry,
        }}
      />
    );

    expect(screen.getByText('网络错误')).toBeInTheDocument();
    expect(screen.getByText('点击重试')).toBeInTheDocument();
  });

  it('should call onRetry when retry button is clicked', () => {
    const onRetry = vi.fn();

    render(
      <TextArea
        text="Some text"
        speaker="assistant"
        isStreaming={false}
        error={{
          message: '网络错误',
          onRetry,
        }}
      />
    );

    fireEvent.click(screen.getByText('点击重试'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('should not render text content when error is shown', () => {
    render(
      <TextArea
        text="Some text"
        speaker="assistant"
        isStreaming={false}
        error={{
          message: '网络错误',
          onRetry: vi.fn(),
        }}
      />
    );

    expect(screen.queryByText('Some text')).not.toBeInTheDocument();
  });
});
