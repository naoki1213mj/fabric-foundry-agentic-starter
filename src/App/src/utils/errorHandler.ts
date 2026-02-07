export interface ApiError {
  status: number;
  statusText: string;
  message?: string;
  error?: unknown;
  endpoint?: string;
  timestamp: string;
}

export interface ErrorResponse {
  error?: {
    message?: string;
    code?: string;
    detail?: unknown;
  };
  message?: string;
  detail?: unknown;
}

export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  API_ERROR = 'API_ERROR',
  PARSE_ERROR = 'PARSE_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

export class ApiErrorHandler {
  /**
   * Logs error detail to console with structured information
   */
  private static logError(error: ApiError): void {
    console.error(`Message: ${error.message || 'No message available'}`);
    if (error.error) {
      console.error('Error detail:', error.error);
    }
  }

  /**
   * Safely extracts error message from any data type
   */
  private static extractErrorMessage(errorData: unknown, status: number): string {
    try {
      // Handle null/undefined
      if (errorData == null) {
        return ApiErrorHandler.getDefaultErrorMessage(status);
      }

      // Handle string responses
      if (typeof errorData === 'string') {
        return errorData;
      }

      // Handle object responses - try to find common error message patterns
      if (typeof errorData === 'object' && errorData !== null) {
        // Try various common error message paths
        const errObj = errorData as Record<string, unknown>;
        const errInner = (errObj.error as Record<string, unknown> | undefined);
        const messagePaths = [
          errInner?.message,
          errObj.message,
          errInner?.detail,
          errObj.detail,
          errObj.error,
          errObj.errorMessage,
          errObj.msg
        ];

        for (const msg of messagePaths) {
          if (msg != null) {
            return typeof msg === 'string' ? msg : JSON.stringify(msg);
          }
        }

        // If no specific message found, stringify the whole object
        return JSON.stringify(errorData, null, 2);
      }

      // Handle other types (number, boolean, etc.)
      return String(errorData);

    } catch (error) {
      console.warn('Failed to extract error message:', error);
      return ApiErrorHandler.getDefaultErrorMessage(status);
    }
  }

  /**
   * Returns default error messages based on HTTP status codes
   */
  private static getDefaultErrorMessage(status: number): string {
    switch (status) {
      case 400:
        return 'Bad request. Please check your input and try again.';
      case 401:
        return 'Authentication failed. Please log in and try again.';
      case 403:
        return 'Access forbidden. You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 429:
        return 'Too many requests. Please wait a moment and try again.';
      case 500:
        return 'Internal server error. Please try again later.';
      case 502:
        return 'Bad gateway. The server is temporarily unavailable.';
      case 503:
        return 'Service unavailable. Please try again later.';
      default:
        return `An unexpected error occurred (Status: ${status}).`;
    }
  }

  /**
   * Handles API response errors - accepts Response object and reads it safely
   */
  public static async handleApiError(
    response: Response,
    endpoint: string,
    fallbackData?: unknown
  ): Promise<{ hasError: boolean; message: string; data?: unknown }> {

    let errorMessage: string;
    let errorData: unknown = null;

    try {
      // Try to read the response body as text first (most compatible)
      const responseText = await response.text();

      if (responseText) {
        try {
          // Try to parse as JSON
          errorData = JSON.parse(responseText);
        } catch (jsonError) {
          // If not JSON, use the text as is
          errorData = responseText;
        }
      }

      errorMessage = ApiErrorHandler.extractErrorMessage(errorData, response.status);

    } catch (readError) {
      console.warn('Failed to read error response:', readError);
      errorMessage = ApiErrorHandler.getDefaultErrorMessage(response.status);
    }

    return {
      hasError: true,
      message: errorMessage,
      data: fallbackData
    };
  }


  /**
   * Handles network/fetch errors with logging
   */
  public static handleNetworkError(
    error: unknown,
    endpoint: string,
    fallbackData?: unknown
  ): { hasError: true; message: string; data?: unknown } {

    const err = error as { message?: string };
    const networkError: ApiError = {
      status: 0,
      statusText: 'Network Error',
      message: err.message || 'Network connection failed',
      error: error,
      endpoint,
      timestamp: new Date().toISOString()
    };

    // Log the error
    ApiErrorHandler.logError(networkError);

    return {
      hasError: true,
      message: 'Network connection failed. Please check your internet connection and try again.',
      data: fallbackData
    };
  }

  /**
   * General error handler that can be used as a catch-all
   */
  public static handleGeneralError(
    error: unknown,
    endpoint: string,
    fallbackData?: unknown
  ): { hasError: true; message: string; data?: unknown } {

    const err = error as { status?: number; statusText?: string; message?: string };
    const generalError: ApiError = {
      status: err.status || 0,
      statusText: err.statusText || 'Unknown Error',
      message: err.message || 'An unexpected error occurred',
      error: error,
      endpoint,
      timestamp: new Date().toISOString()
    };

    // Log the error
    ApiErrorHandler.logError(generalError);

    return {
      hasError: true,
      message: err.message || 'An unexpected error occurred. Please try again.',
      data: fallbackData
    };
  }
}
