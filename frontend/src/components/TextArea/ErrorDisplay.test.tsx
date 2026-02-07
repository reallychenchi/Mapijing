import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorDisplay } from './ErrorDisplay';

describe('ErrorDisplay', () => {
  it('should render error message', () => {
    render(<ErrorDisplay message="测试错误" onRetry={() => {}} />);

    expect(screen.getByText('测试错误')).toBeInTheDocument();
  });

  it('should render default title without error code', () => {
    render(<ErrorDisplay message="测试错误" onRetry={() => {}} />);

    expect(screen.getByText('错误')).toBeInTheDocument();
  });

  it('should render ASR_ERROR title', () => {
    render(<ErrorDisplay message="识别失败" onRetry={() => {}} code="ASR_ERROR" />);

    expect(screen.getByText('语音识别错误')).toBeInTheDocument();
  });

  it('should render LLM_ERROR title', () => {
    render(<ErrorDisplay message="对话失败" onRetry={() => {}} code="LLM_ERROR" />);

    expect(screen.getByText('对话服务错误')).toBeInTheDocument();
  });

  it('should render TTS_ERROR title', () => {
    render(<ErrorDisplay message="合成失败" onRetry={() => {}} code="TTS_ERROR" />);

    expect(screen.getByText('语音合成错误')).toBeInTheDocument();
  });

  it('should render NETWORK_ERROR title', () => {
    render(<ErrorDisplay message="网络错误" onRetry={() => {}} code="NETWORK_ERROR" />);

    expect(screen.getByText('网络连接错误')).toBeInTheDocument();
  });

  it('should render UNKNOWN_ERROR title', () => {
    render(<ErrorDisplay message="未知问题" onRetry={() => {}} code="UNKNOWN_ERROR" />);

    expect(screen.getByText('未知错误')).toBeInTheDocument();
  });

  it('should render retry button', () => {
    render(<ErrorDisplay message="错误" onRetry={() => {}} />);

    expect(screen.getByText('点击重试')).toBeInTheDocument();
  });

  it('should call onRetry when button is clicked', () => {
    const onRetry = vi.fn();
    render(<ErrorDisplay message="错误" onRetry={onRetry} />);

    fireEvent.click(screen.getByText('点击重试'));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('should render error icon', () => {
    render(<ErrorDisplay message="错误" onRetry={() => {}} />);

    const icon = document.querySelector('.error-icon');
    expect(icon).toBeInTheDocument();
  });

  it('should have correct CSS classes', () => {
    render(<ErrorDisplay message="测试" onRetry={() => {}} code="ASR_ERROR" />);

    expect(document.querySelector('.error-display')).toBeInTheDocument();
    expect(document.querySelector('.error-icon')).toBeInTheDocument();
    expect(document.querySelector('.error-title')).toBeInTheDocument();
    expect(document.querySelector('.error-message')).toBeInTheDocument();
    expect(document.querySelector('.retry-button')).toBeInTheDocument();
  });
});
