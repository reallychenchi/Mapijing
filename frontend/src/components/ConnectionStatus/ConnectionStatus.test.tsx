import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConnectionStatus } from './ConnectionStatus';

describe('ConnectionStatus', () => {
  it('should render disconnected state', () => {
    render(<ConnectionStatus state="disconnected" onReconnect={() => {}} />);

    expect(screen.getByText('未连接')).toBeInTheDocument();
    expect(screen.getByText('重新连接')).toBeInTheDocument();
  });

  it('should render connecting state', () => {
    render(<ConnectionStatus state="connecting" onReconnect={() => {}} />);

    expect(screen.getByText('连接中...')).toBeInTheDocument();
    expect(screen.queryByText('重新连接')).not.toBeInTheDocument();
  });

  it('should render connected state', () => {
    render(<ConnectionStatus state="connected" onReconnect={() => {}} />);

    expect(screen.getByText('已连接')).toBeInTheDocument();
    expect(screen.queryByText('重新连接')).not.toBeInTheDocument();
  });

  it('should render error state', () => {
    render(<ConnectionStatus state="error" onReconnect={() => {}} />);

    expect(screen.getByText('连接错误')).toBeInTheDocument();
    expect(screen.getByText('重新连接')).toBeInTheDocument();
  });

  it('should call onReconnect when button is clicked in disconnected state', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus state="disconnected" onReconnect={onReconnect} />);

    fireEvent.click(screen.getByText('重新连接'));

    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it('should call onReconnect when button is clicked in error state', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus state="error" onReconnect={onReconnect} />);

    fireEvent.click(screen.getByText('重新连接'));

    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it('should display correct indicator color for disconnected', () => {
    render(<ConnectionStatus state="disconnected" onReconnect={() => {}} />);

    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toHaveStyle({ backgroundColor: '#999' });
  });

  it('should display correct indicator color for connecting', () => {
    render(<ConnectionStatus state="connecting" onReconnect={() => {}} />);

    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toHaveStyle({ backgroundColor: '#ffc107' });
  });

  it('should display correct indicator color for connected', () => {
    render(<ConnectionStatus state="connected" onReconnect={() => {}} />);

    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toHaveStyle({ backgroundColor: '#28a745' });
  });

  it('should display correct indicator color for error', () => {
    render(<ConnectionStatus state="error" onReconnect={() => {}} />);

    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toHaveStyle({ backgroundColor: '#dc3545' });
  });

  it('should have correct CSS classes', () => {
    render(<ConnectionStatus state="connected" onReconnect={() => {}} />);

    expect(document.querySelector('.connection-status')).toBeInTheDocument();
    expect(document.querySelector('.status-indicator')).toBeInTheDocument();
    expect(document.querySelector('.status-label')).toBeInTheDocument();
  });
});
